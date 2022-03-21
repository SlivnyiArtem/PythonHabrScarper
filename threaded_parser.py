import argparse
import os
import pathlib
import sys
import threading
from concurrent.futures.thread import ThreadPoolExecutor
from bs4 import BeautifulSoup as bs
from urllib.parse import urljoin

from pip._vendor import requests

INDEX = 0


def get_page_urls(articles: int):
    all_articles = []
    cnt = 1
    while True:
        current_url = "https://habr.com/ru/all/page" + str(cnt)
        soup = bs(requests.get(current_url).content, "html.parser")
        if find_articles_on_page(soup, all_articles, articles):
            break
        cnt += 1
    return all_articles


def find_articles_on_page(soup, all_articles, articles):
    for article in soup.find_all("article"):
        article_id = article.attrs.get("id")
        article_url = urljoin("https://habr.com/ru/post/", str(article_id))
        all_articles.append(article_url)
        if len(all_articles) == articles:
            return True
    return False


def download_image(image_url: str, pathname: pathlib.Path):

    response = requests.get(image_url, stream=True)
    filename = os.path.join(pathname, image_url.split("/")[-1])

    with open(filename, "wb") as f:
        for data in response:
            f.write(data)


def futures_download_images_for_many_pages(page_urls: list[str],
                                           threads: int,
                                           out_dir: pathlib.Path):
    executor = ThreadPoolExecutor(max_workers=threads)
    [
        executor.submit(download_images_from_page, page_url, out_dir)
        for page_url in page_urls
    ]
    executor.shutdown()


def get_article_name(page_url: str):
    with threading.Lock():
        soup = bs(requests.get(page_url).content, "html.parser")
        article_name = str(soup.title.string).replace(" / Хабр", "")
        return article_name


def replace_special_symbols(article_name):
    return article_name.replace(":", "").replace("?", "") \
        .replace(">", "").replace("<", "").replace('"', "") \
        .replace("/", "").replace("\\", "").replace("|", "") \
        .replace("*", "")


def download_images_from_page(page_url: str, out_dir: pathlib.Path):
    with threading.Lock():
        image_urls_from_page = get_all_images_urls(page_url)
        if len(image_urls_from_page) == 0:
            return
        article_name = get_article_name(page_url)
        article_name = replace_special_symbols(article_name)
        article_folder = str(out_dir) + "\\" + article_name
        make_dir(article_folder)

        for image_url in image_urls_from_page:
            download_image(image_url, pathlib.Path(article_folder))


def make_dir(out_dir: str):
    with threading.Lock():
        r_out_dir = r'{}'.format(out_dir)
        os.makedirs(r_out_dir, exist_ok=True)


def get_all_images_urls(page_url: str):
    with threading.Lock():
        soup = bs(requests.get(page_url).content, "html.parser")
        urls = []

        for img in soup.find_all("img"):

            img_url_data = img.attrs.get("data-src")

            img_url_no_data = img.attrs.get("src")

            if not img_url_data and not img_url_no_data:
                continue

            img_url_data = urljoin(page_url, img_url_data)

            img_url_no_data = urljoin(page_url, img_url_no_data)

            try:
                q_pos = img_url_data.index("?")
                img_url_data = img_url_data[:q_pos]
            except ValueError:
                pass

            try:
                q_pos = img_url_no_data.index("?")
                img_url_no_data = img_url_no_data[:q_pos]
            except ValueError:
                pass

            if not check_for_bad_pictures(img_url_data, page_url):
                urls.append(img_url_data)
            if not check_for_bad_pictures(img_url_no_data, page_url):
                urls.append(img_url_no_data)

        return urls


def check_for_bad_pictures(img_url, page_url):
    return (img_url.__contains__("mc.yandex.ru/watch/") or
            img_url.__contains__("image-loader.svg") or
            img_url.__contains__(page_url))


def run_scraper(threads: int, articles: int, out_dir: pathlib.Path) -> None:
    page_urls = get_page_urls(articles)

    futures_download_images_for_many_pages(page_urls, threads, out_dir)


def main():
    script_name = os.path.basename(sys.argv[0])
    parser = argparse.ArgumentParser(
        usage=f'{script_name} [ARTICLES_NUMBER] THREAD_NUMBER OUT_DIRECTORY',
        description='Habr parser',
    )
    parser.add_argument(
        '-n', type=int, default=25, help='Number of articles to be processed',
    )
    parser.add_argument(
        'threads', type=int, help='Number of threads to be run',
    )
    parser.add_argument(
        'out_dir', type=pathlib.Path, help='Directory to download habr images',
    )
    args = parser.parse_args()

    run_scraper(args.threads, args.n, args.out_dir)


if __name__ == '__main__':
    main()
