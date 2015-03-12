#!/usr/bin/env python -O
"""This module parses the Amazon product search pages and parses each
product page in the results to extract details about the product. In
this case the product is books.


URL to get 'Fiction and Literature' subject books from Amazon
http://www.amazon.com/b/?node=17

URL to get 'Engineering' subject books from Amazon
http://www.amazon.com/s/ref=lp_283155_nr_n_7?rh=n%3A283155%2Cn%3A%211000%2Cn%3A5&bbn=1000&ie=UTF8&qid=1414297367&rnid=1000

URL to get 'Computers and Technology' subject books from Amazon
http://www.amazon.com/b/?node=173515

"""

import sys
import urllib2
import bs4
import re
import contextlib
import time
import collections
import os
import traceback

html_dump_dir = os.path.join('.', 'amazon_html')
if not os.path.isdir(html_dump_dir):
    os.makedirs(html_dump_dir)

json_table = None
book_count = 0

def dump_json(json_data, file_path):
    """Dump the json data to a file on disk.

    Args:
        json_data: json-like python map/dictionary
        file_path: path to the file into which the json is dumped

    """

    import json

    with open(file_path, 'w') as file_obj:
        print >> file_obj, json.dumps(json_data, indent=4
                                     ,separators=(',', ': '))

def init_json(name, description):
    """Initialize the json structure.

    Args:
        name       : name of the table
        description: description of the table

    Returns: the json-like python map/dictionary

    """

    TEXT    = 'TEXT'
    INTEGER = 'INTEGER'
    FLOAT   = 'FLOAT'

    json_map =  {'table': collections.OrderedDict()}
    json_map['table']['name']        =  name
    json_map['table']['description'] =  description
    json_map['table']['idAttrib']    =  {'name': 'id'
                                        ,'type': INTEGER}
    json_map['table']['attributes']  = [{'name': 'id'
                                        ,'type': INTEGER}
                                       ,{'name': 'ISBN_13'
                                        ,'type': INTEGER}
                                       ,{'name': 'Title'
                                        ,'type': TEXT}
                                       ,{'name': 'Author'
                                        ,'type': TEXT}
                                       ,{'name': 'Price'
                                        ,'type': FLOAT}
                                       ,{'name': 'Publisher'
                                        ,'type': TEXT}
                                       ,{'name': 'Publication_date'
                                        ,'type': TEXT}
                                       ,{'name': 'Pages'
                                        ,'type': INTEGER}]
    json_map['table']['tuples']      = []

    return json_map

def parse_amazon_product_page(url):
    """Parse the Amazon product page.

    Args:
        url: url of the Amazon product page

    """

    global json_table, book_count

    html_data = get_html_data_from_url(url)
    soup = get_soup(html_data)
    body = soup.body

    try:
        try:
            title = body.find('span', id='productTitle').string

        except AttributeError:  # 'NoneType' object has no attribute 'string'
            title  = body.find('span', id='btAsinTitle').string

        price = float(body.find('span', class_='a-color-price').string.strip(
                        ).lstrip('$'))

        #author = body.find('div' , id=['byLine', 'byline']).find(name='a'
        #                 ).find('span', class_='author notFaded')
        try:
            author = body.find('div' , id=['byLine', 'byline']).find(name='a',
                             class_='contributorNameID').string

        except AttributeError:
            try:
                author = body.find('div' , id=['byLine', 'byline'])(name='a'
                                 )[-2].string

            except IndexError:
                author = body.find('div' , id=['byLine', 'byline']).find(name=
                                 'a').string

        product_details = body.find('div', id='detail-bullets')

        pub_details = product_details.find('b', text='Publisher:').next_sibling
        publisher   = pub_details.split(';')[0].split('(')[0].strip()
        pub_date    = pub_details.split('(')[-1].rstrip(')').strip()

        try:
            pub_date = time.strftime('%m/%d/%Y', time.strptime(pub_date
                                                          ,'%B %d, %Y'))

        # not in MM/DD/YYYY format
        # time data u'June 1982' does not match format '%B %d, %Y'
        except ValueError:
            pass  # keep it as is

        try:
            isbn_13 = int(product_details.find('b', text='ISBN-13:'
                              ).next_sibling.strip().replace('-', ''))

        except AttributeError:
            # look for ISBN-10
            isbn_13 = int(product_details.find('b', text='ISBN-10:'
                              ).next_sibling.strip())

        for product_detail in product_details('b'):
            if 'pages' in product_detail.next_sibling.string:
                num_pages = int(product_detail.next_sibling.string.strip(
                                    ).split()[0])
                break

        if '/' in title:
            title = title.replace('/', '|')
        with open(os.path.join(html_dump_dir, '%s_%s.html' % (title, isbn_13))
                 ,'w') as file_object:
            print >> file_object, html_data

        book_tuple = collections.OrderedDict()
        book_count += 1
        book_tuple['id']               = book_count
        book_tuple['ISBN_13']          = isbn_13
        book_tuple['Title']            = title
        book_tuple['Author']           = author
        book_tuple['Price']            = price
        book_tuple['Publisher']        = publisher
        book_tuple['Publication_date'] = pub_date
        book_tuple['Pages']            = num_pages

        json_table['table']['tuples'].append(book_tuple)

    except Exception:
        traceback.print_exc()
        print >> sys.stderr, 'Error parsing product page: %s' % url
        raise

def parse_amazon_product_search_page(url, limit=5000):
    """Parse the products returned from Amazon search result.

    Caution! this is a recursive function :p

    Args:
        url         : url of the Amazon product search page
        limit       : no. of products to parse before returning. Cannot
                      be guaranteed if the no. of results < limit

    """

    num_products = 0

    while True:
        soup = get_soup(get_html_data_from_url(url))
        search_results = soup.body(id=re.compile('^result_[0-9]+$'))

        for result in search_results:
            try:
                product_data = result.find('div', class_='data')
                product_url  = product_data.find('a', class_='title')['href']

                parse_amazon_product_page(product_url)

            # some missing information with this particular product.
            # Ignore it
            except Exception:
                continue

            num_products += 1
            if num_products == limit:
                return

        else:  # yet to reach limit, go to next page
            try:
                url = 'www.amazon.com' + soup.body.find('div', id='pagn',
                          class_='pagnHy').find('a', id='pagnNextLink')['href']

            # can no longer paginate. Reached the end of search results
            # generally 100th page as Amazon generally returns only a
            # max of 100 pages for any search query
            # 'NoneType' object has no attribute '__getitem__'
            except TypeError:
                return

def get_soup(ml_data):
    """Beautiful soup is Python library for pulling data out of HTML and
    XML files.

    Args:
        ml_data: HTML or XML data as a string

    Returns:
        a Python object which a complex tree of Python objects

    """

    return bs4.BeautifulSoup(ml_data)

def get_html_data_from_url(url):
    """Gets HTML data as a string from the url.

    Args:
        url: string which represents the URL of the web page

    Returns:
        a string containing the HTML data

    Raises:
        URLError: on errors

    """

    if not url.startswith('http://'):
        url = 'http://%s' % url

    request = urllib2.Request(url, headers = {'User-Agent':
                 ('User-Agent:Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_5) '
                  'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/38.0.2125.101'
                  ' Safari/537.36')})
    with contextlib.closing(urllib2.urlopen(request)) as file_obj:
        return file_obj.read()

def _parse_cmd_line_opts_args():
    """Parse the command-line options and arguments."""

    import argparse

    num_products = 5000

    parser = argparse.ArgumentParser(description=('This module parses the '
                     'Amazon product search pages and parses each product page'
                     ' in the results to extract details about the product. In'
                     ' this case the product is books.'))

    parser.add_argument('--version', action='version', version='%(prog)s 1.0')
    parser.add_argument('-n', '--numproducts', nargs='?', default=num_products
                       ,type=int#, choices=range(1, 100000)
                       ,help=('The number of products to parse. [default: '
                              '%(default)s]'))
    parser.add_argument('urls', nargs='+', help=('The URLs of the product '
                        'search pages from which the products are parsed'))

    args = parser.parse_args()

    return args.numproducts, args.urls

def main():
    """main function."""

    limit, urls = _parse_cmd_line_opts_args()

    global json_table
    json_table = init_json('Amazon', 'Books from Amazon.com')

    try:
        for amazon_url in urls:
            try:
                parse_amazon_product_search_page(amazon_url, limit)

            except Exception:
                print >> sys.stderr, 'Error parsing URL: %s' % amazon_url
                traceback.print_exc()

    finally:
        dump_json(json_table, 'amazon.json')

if __name__ == '__main__':
    main()
