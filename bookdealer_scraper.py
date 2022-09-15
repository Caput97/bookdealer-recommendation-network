from urllib.parse import urljoin
from bs4 import BeautifulSoup
from os import path
import requests
import logging
import re
import csv

logging.basicConfig(level=logging.DEBUG)

DOMAIN = 'https://www.bookdealer.it/'


def main():
    path = '/i-consigli-dei-librai'
    # Compose URl
    book_rec_url = urljoin(DOMAIN, path)
    logging.info(f'Parsing {book_rec_url}')
    book_rec_soup = get_soup(book_rec_url)
    last_page_button = book_rec_soup.find_all('a',{'class':'next-btn'})[1]
    # Get last page number (after substring '?pag=')
    last_page = int(last_page_button['href'][5:])    
    for page in range(last_page,last_page+1):
        books_in_page = list()
        logging.info(f'Parsing page {page}')
        page_soup = get_soup(f'{book_rec_url}?pag={page}')
        book_headers = page_soup.find_all('div', {'class':'product-header'})
        # Parse book data from every book in page
        for book_header in book_headers:
            book_path = book_header.select_one('a[href*=\/libro\/]')['href']
            book_url = urljoin(DOMAIN, book_path)
            book_data = parse_book_data(book_url)
            logging.info(f'{book_data}')
            books_in_page.append(book_data)
        logging.info(f'Page {page} parsing completed')
        write_csv(data = books_in_page, filename='data/bd-recommendations.csv')
    logging.info('Parsing completed')


def get_soup(url):
    source = requests.get(url)
    soup = BeautifulSoup(source.text, 'html.parser')
    return soup


def parse_book_data(url_book):
    logging.info(f'Parsing book {url_book}')
    book_data = dict()
    book_soup = get_soup(url_book)
    book_info = book_soup.find('div', {'class':'product-details-info'})
    # Title
    book_data['titolo'] = book_info.find('h3',{'class':'product-title'}
                                         ).string
    # Price
    price_tag = book_info.find('span', {'class':'price-new'}).string
    # Try formatting price in as int
    try:
        formatted_price = int(re.search(r'(\d+),\d\d €', price_tag).group(1))
    except:
        logging.debug(f'Cannot convert price tag \"{price_tag}\"')
        book_data['prezzo'] = price_tag
    # Additional info
    # Get str format (easier to parse using re)
    add_info = book_info.find('ul', {'class':'list-unstyled'}).text
    # Labels for matching
    add_info_labels = ['Autore','Editore', 'Isbn', 'Categoria',
                       'Numero pagine','Data di Uscita']
    for add_info_label in add_info_labels:
        # Find info
        match = re.search(fr'{add_info_label}: (.+)\n', add_info)
        # Format label
        add_info_label = add_info_label.replace(' ','-').lower()
        # Add information do dict
        try:
            book_data[add_info_label] = match.group(1)
        except AttributeError:
            logging.debug(f'Label \"{add_info_label.upper()}\" missing')
            book_data[add_info_label] = None
    # List of indie bookstores that suggest the book
    try:
        bookstores = book_soup.find('div', {'class':'w-consigliato-da'}
                                    ).select('a[href*=\/libreria\/]')
    except:
        logging.debug('No bookstores found')
        bookstores = None
    if bookstores:
        # Number of recommendations
        book_data['raccomandazioni-ricevute'] = len(bookstores)
        # Get bookstore ids
        bookstores = [bookstore['href'][len('/libreria/'):]
                      for bookstore in bookstores]
        book_data['consigliato-da'] = ', '.join(bookstores)
    else:
        # Bookstores list may be missing
        # e.g. https://www.bookdealer.it/libro/9788804586890/la-breve-favolosa-vita-di-oscar-wao
        book_data['raccomandazioni-ricevute'] = None
        book_data['consigliato-da'] = None
    return book_data


def write_csv(data, filename):
    # Check if file already exists to write column names only once
    if path.exists(filename):
        write_column_names = False
        logging.info('Creating CSV file')
    else:
        write_column_names = True
    # Write or keep writing CSV file
    with open(filename, 'a+', newline='') as output_file:
        dict_writer = csv.DictWriter(output_file, data[0].keys())
        if write_column_names:
            logging.info('Writing column names')
            dict_writer.writeheader()
        logging.info('Adding books')
        dict_writer.writerows(data)


if __name__ == '__main__':
    main()

