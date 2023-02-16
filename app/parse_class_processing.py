import csv
import time
import requests
import multiprocessing

from dataclasses import dataclass, fields, astuple
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from concurrent.futures import ProcessPoolExecutor, wait

from parse import Quote, Author


@dataclass
class ParseQuote:
    base_url = "https://quotes.toscrape.com"
    authors_url = set()
    quote_fields = [field.name for field in fields(Quote)]
    author_fields = [field.name for field in fields(Author)]
    result_quotes = []
    result_authors = []

    def _parse_single_quote(self, page_soup: BeautifulSoup) -> None:
        self.result_quotes.append(Quote(
            text=page_soup.select_one(".text").text,
            author=page_soup.select_one(".author").text,
            tags=[tag.text for tag in page_soup.select(".tag")]
        ))

    def _parse_single_author(self, page_soup: BeautifulSoup) -> None:
        self.result_authors.append(Author(
            biography=page_soup.select_one(
                ".author-details"
            ).text.replace("\n", " "),
        ))

    @staticmethod
    def _write_list_in_file(
            name_path_file_csv: str,
            name_file: list[object],
            fields: list[fields],
    ) -> None:
        with open(name_path_file_csv, "w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(fields)
            writer.writerows([astuple(name) for name in name_file])

    def _get_authors_page_soup(
            self,
            page_soup: list[BeautifulSoup]
    ) -> list[BeautifulSoup]:
        result_authors = []
        for author_url in page_soup:
            url = urljoin(
                self.base_url,
                author_url.select_one("a").get("href")
            )
            if url not in self.authors_url:
                page = requests.get(url).content
                result_authors.append(BeautifulSoup(page, "html.parser"))
            self.authors_url.add(url)
        return result_authors

    def _get_all_page_soup(self) -> list[BeautifulSoup]:
        result_page_soup = []

        page = requests.get(self.base_url).content
        page_soup = BeautifulSoup(page, "html.parser")
        result_page_soup.append(page_soup.select(".quote"))

        while page_soup.find("li", class_="next"):
            pagination = page_soup.select_one(".next > a").get("href")
            next_url = urljoin(self.base_url, pagination)
            page = requests.get(next_url).content
            page_soup = BeautifulSoup(page, "html.parser")
            result_page_soup.append(page_soup.select(".quote"))
        return result_page_soup

    def _get_quotes(self, list_page_soup: BeautifulSoup) -> None:
        for page_soup in list_page_soup:
            for quote in page_soup:
                self._parse_single_quote(quote)

    def _get_authors(self, list_page_soup: BeautifulSoup) -> None:
        for page_soup in list_page_soup:
            authors_page_soup = self._get_authors_page_soup(page_soup)
            for author in authors_page_soup:
                self._parse_single_author(author)

    def main(self) -> None:
        result_page_soup = self._get_all_page_soup()

        tasks = []
        with ProcessPoolExecutor(
                multiprocessing.cpu_count() - 1
        ) as executor:
            tasks.append(executor.submit(self._get_quotes, result_page_soup))
            tasks.append(executor.submit(self._get_authors, result_page_soup))
        wait(tasks)

        # task1 = multiprocessing.Process(
        #     target=self._get_quotes, args=(result_page_soup,)
        # )
        # task2 = multiprocessing.Process(
        #     target=self._get_authors, args=(result_page_soup,)
        # )
        # task1.start()
        # task2.start()
        # task1.join()
        # task2.join()

        # self._get_quotes(result_page_soup)
        # self._get_authors(result_page_soup)

        self._write_list_in_file(
            "quotes.csv",
            self.result_quotes,
            self.quote_fields
        )
        self._write_list_in_file(
            "authors.csv",
            self.result_authors,
            self.author_fields
        )


if __name__ == "__main__":
    star = time.perf_counter()

    quotes = ParseQuote()
    quotes.main()

    print(f"Elapsed: {time.perf_counter() - star}")
