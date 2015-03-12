import urllib2
import sys
import bs4
import re
import contextlib
import time
import collections
import os
from bs4 import BeautifulSoup
import math
import amazon
import traceback

json_table = None
total_count = 1

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
        URLErro
        r: on errors

    """

    if not url.startswith('http://'):
        url = 'http://%s' % url

    request = urllib2.Request(url, headers = {'User-Agent':
                 ('User-Agent:Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_5) '
                  'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/38.0.2125.101'
                  ' Safari/537.36')})
    with contextlib.closing(urllib2.urlopen(request)) as file_obj:
        return file_obj.read()


def fetchBook(url):

    global json_table
    global total_count

    book_attrs = collections.OrderedDict()
    allowed_attrs = ['Title:', 'Publisher:', 'Pages:', 'Publication date:', 'ISBN-13:', 'Author:', 'Price:']

    bookData = urllib2.urlopen(url).read()
    soup = BeautifulSoup(bookData)

    data_regex = re.compile('product-title-1')
    main_div = soup.find('div', id='product-title-1')
    if(main_div):
        if(main_div.next.next):
            title = main_div.next.next.strip()
        else:
            return
    else:
        return

    timestamp = int(time.time())
    op = open(main_div.next.next.strip() + '_' + `timestamp` + '.html','w')
    op.write(bookData)
    op.close()

    #parsing Price
    price = ''
    soup = BeautifulSoup(bookData)
    data_regex = re.compile('price hilight')
    main_div = soup.find('div', attrs={'class' : data_regex})
    if(main_div):
        if(main_div.next):
            price = main_div.next.strip()

    # parsing Author
    author = ''
    soup = BeautifulSoup(bookData)
    data_regex = re.compile('subtle')
    main_div = soup.find('a', attrs={'class' : data_regex})
    if(main_div):
        if(main_div.next):
            author = main_div.next.strip()

    soup = BeautifulSoup(bookData)
    data_regex = re.compile('product-details box')
    main_div = soup.find('div', attrs={'class' : data_regex})

    if(main_div):
        main_div = soup.find('div', attrs={'class' : data_regex}).findAll('li')
    else:
        return

    first = 1
    attr = ""
    val = ""
    for book in main_div:
        if(book.next):
            if(first == 1):
                if(book.next.next):
                    if(book.next.next.next):
                        if(book.next.next.nextSibling):
                            val = book.next.next.nextSibling.strip()
                first = 0
            else:
                if(book.next.next):
                    if(book.next.next.next):
                        val = book.next.next.next

            if(book.next.next):
                attr = book.next.next

            attr = attr.string.strip()
            if(attr in allowed_attrs):
                book_attrs[attr] = val

    book_tuple = collections.OrderedDict()
    book_tuple = {'id': total_count,'ISBN-13': book_attrs['ISBN-13:']
                    ,'Title': title, 'Author': author,'Price': price
                    ,'Publisher': book_attrs['Publisher:']
                    ,'Publication date': book_attrs['Publication date:']
                    ,'Pages': book_attrs['Pages:']}

    total_count = total_count + 1
    json_table['table']['tuples'].append(book_tuple)



def fetchURL(url, page):

    trial = 0;
    while(1):
        trial = trial + 1
        html_data = get_html_data_from_url(url)
        soup = get_soup(html_data)
        body = soup.body


        categories_regex = re.compile('title')
        main_div = body.findAll('a', attrs={'class' : categories_regex})
        if(len(main_div) == 0 and trial < 10):
            continue;

        break;

    if(len(main_div) == 0):
        return 0


    op = open('homepage_' + `page` + '.html', "w")
    op.write(html_data)

    for category in main_div:
        if category:
            try:
                fetchBook(category['href'])
            except:
                traceback.print_exc()

    op.close()
    return 1


def main():

    try:
        global json_table
        json_table = amazon.init_json('Barnesandnoble')

        categories = 0
        res = 0
        urls = ['9', '13' , '25']
        while(categories < 3):
            startat = 1;
            url1 = 'http://www.barnesandnoble.com/s/?aud=tra&dref=' + urls[categories] + '&fmt=physical&sort=SA&startat='
            url2 = '&store=BOOK&view=grid'

            page = 1
            res = 0
            while(res <= 40):
                url = url1 + `startat` + url2
                try:
                    res = res + fetchURL(url, page)
                    page = page + 1
                except Exception:
                    traceback.print_exc()
                startat = startat + 30

            categories = categories + 1

    except Exception:
        traceback.print_exc()

    finally:
        amazon.dump_json(json_table, 'barnesandnoble.json')


main()

