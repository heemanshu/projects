#!/usr/bin/python2.7
"""This accept the data from 2 tables in json format and performs
blocking on them on a particular matching attribute to generate a
candidate set in the csv format on which the data matching can be
performed efficiently.

Using inverted index on the matching attribute (Publisher) to generate
the candidate set.


"""

import sys
import json
import collections
import time

def get_csv_header(table_1, prepend_1, table_2=None, prepend_2=None, labeling=False):
    """Writes the csv header looking at the table schema in table_1.

    Args:
        table_1  : dictionary containing the schema of the table 1
        prepend_1: prepend to all the attributes from table_1 in the
                   blocked table
        table_2  : dictionary containing the schema of the table 2
        prepend_1: prepend to all the attributes from table_2 in the
                   blocked table
        labeling : add the label header if true

    Returns:
        a list containing the csv header fields

    """

    ti_id_attr = table_1['table']['idAttrib']
    t2_id_attr = table_1['table']['idAttrib']

    if table_2 is not None:
        header = '"pairId:INTEGER",'

        header = '%s"%s.%s:%s","%s.%s:%s",' % (header, prepend_1,
                         ti_id_attr['name'], ti_id_attr['type'], prepend_2,
                         t2_id_attr['name'], t2_id_attr['type'])

    for attr in table_1['table']['attributes']:
        if table_2 is not None and attr['name'] == ti_id_attr['name']: continue
        header = '%s"%s.%s:%s",' % (header, prepend_1, attr['name']
                                   ,attr['type'].upper())

    if table_2 is None:
        return header.rstrip(',')

    for attr in table_2['table']['attributes']:
        if attr['name'] == t2_id_attr['name']: continue
        header = '%s"%s.%s:%s",' % (header, prepend_2, attr['name']
                                   ,attr['type'].upper())

    header = header.rstrip(',')

    if labeling:
        header = '%s,"label:INTEGER"' % header

    return header

def do_blocking(table_1, prepend_1, table_2, prepend_2, csv_file
               ,blocking_attr, labeling=False):
    """Given 2 dictionaries containing the data of 2 tables, does
    blocking to generate the candidate set and writes it into the
    csv_file.

    Args:
        table_1      : dictionary containing the data of table 1
        prepend_1    : prepend to all the attributes from table_1 in the
                       blocked table
        table_2      : dictionary containing the data of table 2
        prepend_1    : prepend to all the attributes from table_2 in the
                       blocked table
        csv_file     : file into which the blocked data is written in
                       csv format
        blocking_attr: the attribute in the table on which the blocking
                       is done
        labeling     : label the records as 0 or 1 based on whether they
                       match with the same ISBN

    """

    header = get_csv_header(table_1, prepend_1, table_2, prepend_2, labeling)

    t1_id = table_1['table']['idAttrib']['name']
    t2_id = table_1['table']['idAttrib']['name']

    # insert book tuples from table_2 into a dictionary indexed on the
    # matching attribute so that lookups of books from table_1 in
    # table_2 is efficient
    t2_idxd = collections.defaultdict(list)
    for book_tuple in table_2['table']['tuples']:
        t2_idxd[book_tuple[blocking_attr]].append(collections.OrderedDict(
                                                                   book_tuple))

    pair_id = 1
    isbn_count = 0
    with open(csv_file, 'wb') as csv_fo:
        print >> csv_fo, header

        # iterate through the tuples in table_1 and match it with
        # table_2 on the blocking_attr using the t2_idxd
        for t1_tup in table_1['table']['tuples']:
            blking_attr_val = t1_tup[blocking_attr]
            t1_pub_date_str = t1_tup['Publication_date']
            try:
                t1_pub_date = time.strptime(t1_pub_date_str, '%m/%d/%y')
                t1_pub_yr  = t1_pub_date.tm_year
                t1_pub_mth = t1_pub_date.tm_mon
                t1_tup['Publication_date'] = time.strftime('%m/%d/%Y', t1_pub_date)
            except ValueError:
                try:
                    t1_pub_date = time.strptime(t1_pub_date_str, '%m/%d/%Y')
                    t1_pub_yr  = t1_pub_date.tm_year
                    t1_pub_mth = t1_pub_date.tm_mon
                    t1_tup['Publication_date'] = time.strftime('%m/%d/%Y', t1_pub_date)
                except ValueError:
                    try:
                        t1_pub_date = time.strptime(t1_pub_date_str, '%B %Y')
                        t1_pub_yr  = t1_pub_date.tm_year
                        t1_pub_mth = t1_pub_date.tm_mon
                        t1_tup['Publication_date'] = time.strftime('%m/%Y', t1_pub_date)
                    except ValueError:
                        t1_pub_yr  = time.strptime(t1_pub_date_str, '%Y').tm_year
                        t1_pub_mth = None

            if blking_attr_val in t2_idxd:
                for t2_tup in t2_idxd[blking_attr_val]:
                    if t1_tup['ISBN_13'] == t2_tup['ISBN_13']:
                        isbn_count += 1
                    t2_pub_date_str = t2_tup['Publication_date']
                    try:
                        t2_pub_date = time.strptime(t2_pub_date_str, '%m/%d/%y')
                        t2_pub_yr  = t2_pub_date.tm_year
                        t2_pub_mth = t2_pub_date.tm_mon
                        t2_tup['Publication_date'] = time.strftime('%m/%d/%Y', t2_pub_date)
                    except ValueError:
                        try:
                            t2_pub_date = time.strptime(t2_pub_date_str, '%m/%d/%Y')
                            t2_pub_yr  = t2_pub_date.tm_year
                            t2_pub_mth = t2_pub_date.tm_mon
                            t2_tup['Publication_date'] = time.strftime('%m/%d/%Y', t2_pub_date)
                        except ValueError:
                            try:
                                t2_pub_date = time.strptime(t2_pub_date_str, '%B %Y')
                                t2_pub_yr  = t2_pub_date.tm_year
                                t2_pub_mth = t2_pub_date.tm_mon
                                t2_tup['Publication_date'] = time.strftime('%m/%Y', t2_pub_date)
                            except ValueError:
                                t2_pub_yr = time.strptime(t2_pub_date_str, '%Y').tm_year
                                t2_pub_mth = None

                    if t1_pub_yr != t2_pub_yr:
                        if t1_tup['ISBN_13'] == t2_tup['ISBN_13']:
                            print 'year', t1_tup, t2_tup
                        continue
                    if t1_pub_mth != t2_pub_mth:
                        if t1_pub_mth is not None and t2_pub_mth is not None:
                            if t1_tup['ISBN_13'] == t2_tup['ISBN_13']:
                                print 'month', t1_tup, t2_tup
                            continue
                    matched_tuple = '"%s","%s","%s"' % (pair_id, t1_tup[t1_id]
                                                       ,t2_tup[t2_id])

                    # append attributes from table 1
                    for attr in t1_tup:
                        if attr == t1_id: continue
                        if (    isinstance(t1_tup[attr], str)
                            and '"' in t1_tup[attr]):
                            t1_tup[attr] = t1_tup[attr].replace('"', '""')
                        matched_tuple = '%s,"%s"' % (matched_tuple
                                                    ,t1_tup[attr])

                    # append attributes from table 2
                    for attr in t2_tup:
                        if attr == t2_id: continue
                        if (    isinstance(t2_tup[attr], str)
                            and '"' in t2_tup[attr]):
                            t2_tup[attr] = t2_tup[attr].replace('"', '""')
                        matched_tuple = '%s,"%s"' % (matched_tuple
                                                    ,t2_tup[attr])
                    if labeling:
                        if t1_tup['ISBN_13'] == t2_tup['ISBN_13']:
                            label = 1
                        else:
                            label = 0
                        matched_tuple = '%s,"%s"' % (matched_tuple, label)

                    pair_id += 1
                    print >> csv_fo, matched_tuple.encode('utf8')
    print isbn_count

def load_json(json_file_path):
    """Loads the json data present in the file located at json_file_path
    to a python dictionary.

    Args:
        json_file_path: path of the file containing the json data

    Returns:
        python dictionary containing the json data

    """

    with open(json_file_path) as json_fo:
        return json.load(json_fo, object_pairs_hook=collections.OrderedDict)

def main():
    """Load data of the 2 tables from json files and perform the
    blocking."""

    json_fpath_1 = sys.argv[1]
    json_fpath_2 = sys.argv[2]
    csv_file     = sys.argv[3]

    try:
        label = sys.argv[4]
        label = True
    except IndexError:
        label = False

    table_1 = load_json(json_fpath_1)
    table_2 = load_json(json_fpath_2)

    prepend_1     = 'amzn'
    prepend_2     = 'bnn'
    blocking_attr = 'Publisher'

    do_blocking(table_1, prepend_1, table_2, prepend_2, csv_file
               ,blocking_attr, label)

if __name__ == '__main__':
    main()
