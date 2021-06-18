import json
import logging
import os.path as path
import pathlib
from typing import Union

import pywikibot
import pywikibot.textlib as textlib
import sys

DIR_TMP = "tmp"
PATH_CONFIG = path.join(DIR_TMP, "config.json")
EDIT_SUMMARY = "PWB: move copy images from commons.mediawiki.org"
pathlib.Path(DIR_TMP).mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("bot_imtransfer")
logger.setLevel(logging.INFO)
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s[%(name)s][%(levelname)s] %(message)s', datefmt='%H:%M:%S')
ch.setFormatter(formatter)
logger.addHandler(ch)


class Config:
    CODE_HEAD = '\033[95m'
    CODE_BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    CODE_END = '\033[0m'

    @staticmethod
    def bold_head(s: str):
        return f"{Config.CODE_HEAD}{Config.CODE_BOLD}{s}{Config.CODE_END}{Config.CODE_END}"

    def __init__(self, test=False, mute=False, auto=False):
        self.test = test
        self.mute = mute
        self.auto = auto
        try:
            with open(PATH_CONFIG, 'rb') as fh:
                self.config = json.loads(fh.read().decode('utf-8'))
        except FileNotFoundError:
            self.config = {"cate_map": {}}

    def default_rule(self, s: str) -> Union[bool, None, str]:
        """ Applied of no rules found in config JSON.
        Return None to allow other rules like user input
        Return False to ignore the input class
        """
        raise NotImplementedError()

    def auto_rule(self, s: str) -> Union[bool, str]:
        """ Applied when self.auto is turned on, or user input is
        an empty string.
        Return False to ignore the input class.
        Must be complete and handle all string input.
        """
        raise NotImplementedError()

    def _app_default_rule(self, s: str):
        out = self.default_rule(s)
        if out is not None:
            logger.info(f"Defuault rule applied to {s}, got {repr(out)}")
        return out

    def _app_auto_rule(self, s: str):
        out = self.auto_rule(s)
        logger.info(f"Auto rule applied to '{s}', got {repr(out)}")
        return out

    def cat_map(self, cat: pywikibot.Category, is_re=False) -> Union[bool, str]:
        cat_name = cat.title(with_ns=False)
        if cat_name not in self.config["cate_map"]:
            name = self._app_default_rule(cat_name)
            if name is None and self.auto:
                name = self._app_auto_rule(cat_name)
            if name is None:
                prompt = f"Please input category in target site which matches '{self.bold_head(cat_name)}' in " \
                         f"source site; Type 'no' to discard this category"
                if is_re:
                    prompt = "[CURRENTLY THIS CATEGORY IS USED IN A REDIRECT PAGE]\n" + prompt
                name = input(prompt)

            if name == "":
                name = self._app_auto_rule(cat_name)
            elif isinstance(name, str) and name.lower() == "no":
                name = False
            self.config['cate_map'][cat_name] = name
            self.save()
        return self.config["cate_map"][cat_name]

    def save(self):
        s = json.dumps(self.config, indent=4, sort_keys=True)
        with open(PATH_CONFIG, 'wb') as fh:
            fh.write(s.encode("utf-8"))


def sync_cate(source: pywikibot.Page, target: pywikibot.Page, config: Config, is_re=False, ):
    new_cats = []
    old_cats = list(target.categories())
    for c_source in source.categories():
        c_target_name = config.cat_map(c_source, is_re=is_re)
        if not c_target_name:
            continue
        new_cat = pywikibot.Category(target.site, c_target_name)
        c_target = pywikibot.Category(target.site, c_source.title(with_ns=False))
        if c_source in old_cats:
            target.text = textlib.replaceCategoryInPlace(target.text, c_target, new_cat, target.site)
        else:
            new_cats.append(new_cat)
    target.text = textlib.replaceCategoryLinks(target.text, new_cats, target.site, addOnly=True)


def getFinalRedirectTarget(page: pywikibot.Page):
    while page.isRedirectPage():
        page = page.getRedirectTarget()
    return page


def get_files(target: pywikibot.Site, summary: dict):
    scanned_files = set()
    all_pages = list(target.allpages())
    for i, p in enumerate(all_pages):
        for f in p.imagelinks():
            scanned_files.add(f.title())
        logger.info(f"Page scanned: {i + 1}/{len(all_pages)}")

    summary["page_scanned"] = len(all_pages)
    summary["file_scanned"] = len(scanned_files)
    return scanned_files


def save_page(page: pywikibot.Page, config: Config, summary):
    if not config.test:
        page.save(summary=EDIT_SUMMARY)
    elif not config.mute:
        width = 80
        page_width = len(page.title()) + 2
        l_half = (width - page_width) // 2
        l_half = max(2, l_half)
        r_half = width - page_width - l_half
        r_half = max(2, r_half)
        logger.info(
            f"[TEST MODE]: Simulate saving page:\n"
            f"{'=' * l_half}'{page.title()}'{'=' * r_half}\n"
            f"{page.text}\n{'=' * (l_half + page_width + r_half)}\n")
    summary["page_saved"] += 1


def upload_file(page: pywikibot.FilePage, source: str, config: Config, summary, text=None, report_success=None):
    if not config.test:
        page.upload(source, text=text, report_success=report_success)
    elif not config.mute:
        logger.info(f"[TEST MODE]: UPLOAD file to page '{page.title()}' with '{source}'")
    summary["uploaded"] += 1


def sync_files(source: pywikibot.Site, target: pywikibot.Site, scanned_files: set, summary: dict, config: Config):
    viewed_source_cat = set()
    for i, f in enumerate(scanned_files):
        f_target = pywikibot.FilePage(target, f)
        if not f.endswith(".svg"):
            summary["non_svg"] += 1
            continue
        f_source = pywikibot.FilePage(source, f)
        if not f_source.exists():  # not found in source site
            summary["not_found"] += 1
            continue

        # Solve redirect
        redirected = False
        while f_source.isRedirectPage():
            # create and save redirect page on target site
            if f_target.exists() and not f_target.isRedirectPage():
                f_source = getFinalRedirectTarget(f_source)
                logger.warning(
                    f"Matches {f_target.title()} with {f_source.title()} because of mismatched redirect levels.")
                break

            f_target.set_redirect_target(
                pywikibot.Page(target, f_source.getRedirectTarget().title(with_ns=True)), save=False, force=True)
            sync_cate(f_source, f_target, config, is_re=True)
            save_page(f_target, config, summary)
            f_target = f_target.getRedirectTarget()
            f_source = f_source.getRedirectTarget()
            redirected = True
        if redirected:
            summary["redirected"] += 1

        # get images
        for cat_source in f_source.categories():
            if cat_source in viewed_source_cat:
                continue
            cat_target_name = config.cat_map(cat_source)
            if not cat_target_name:
                logger.info(f"Skipped {cat_source.title(with_ns=False)} when checking {f_target}")
                viewed_source_cat.add(cat_source)
                continue

            for sibling_source in cat_source.members(namespaces="File"):
                sibling_target = pywikibot.FilePage(target, sibling_source.title(with_ns=False))
                if not sibling_target.exists():
                    upload_file(sibling_target, sibling_source.get_file_url(), config, summary, text="",
                                report_success=True)
                    sync_cate(sibling_source, sibling_target, config)
                    save_page(sibling_target, config, summary)
                else:
                    sync_cate(sibling_source, sibling_target, config)
                    save_page(sibling_target, config, summary)
            viewed_source_cat.add(cat_source)
        logger.info(f"\033[92mFile processed: {i + 1}/{len(scanned_files)}\033[0m\n\n")


def main(source: pywikibot.Site, target: pywikibot.Site, conf: Config):
    summary = {
        "file_scanned": 0,
        "page_scanned": 0,
        "page_saved": 0,
        "non_svg": 0,
        "not_found": 0,
        "uploaded": 0,
        "redirected": 0,
    }

    file_set = get_files(target, summary)
    sync_files(source, target, file_set, summary, conf)
    print(json.dumps(summary))


if __name__ == '__main__':
    class ShmetroConf(Config):
        def default_rule(self, s: str) -> Union[bool, None, str]:
            if s.lower().startswith("bsicon/railway/set u"):
                return s
            if s.lower().startswith("bsicon/railway/set"):
                return False
            return

        def auto_rule(self, s: str) -> Union[bool, None, str]:
            if "bsicon" in s.lower():
                return s
            return False


    config = ShmetroConf(test=True, mute=False, auto=False)
    commons = pywikibot.Site("commons", "commons")
    shmetro = pywikibot.Site("zh", "shmetro")
    main(commons, shmetro, config)
