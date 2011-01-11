#!/usr/bin/env python
# coding: utf-8

# My Opera Graph tool

from lxml import etree
from urllib import quote, unquote
from time import sleep
from zlib import crc32

import httplib2
import sys

__all__ = [
    'graph2dot',
    'get_countries',
    'get_country_top50_users',
    'get_friends_of_user',
    'get_user_by_login',
    'get_foaf_of_users',
]

SITE_ADDR = 'http://my.opera.com'
_http = httplib2.Http(".cache")
_parse = lambda content: etree.fromstring(content, parser=etree.HTMLParser())


def graph2dot(graph):
    ''' Format python dict to GraphVIZ dot file '''
    tmpl = \
    '''digraph FOAF {
    %s

    %s
    overlap=false
    label="FOAF Graph of my.opera.com"
    fontsize=8;
    }
    '''
    crc = lambda c: abs(crc32(c.encode('utf-8')))
    style = '%s[label="%s", shape=box, color=blue];\n'
    style_buff = ''
    for i in graph.keys():
        style_buff += style % (crc(i),
                               i.replace('"', r'\"'))
    # some vertices may not appear in keys
    # add such vertices to graph too.
    s = set()
    for vl in graph.values():
        for v in vl:
            if v not in graph:
                s.add(v)
    for i in s:
        style_buff += style % (crc(i),
                               i.replace('"', r'\"'))
    s = '%s->%s;\n'
    buff = ''
    for k, v_list in graph.items():
        src_key = crc(k)
        for v in v_list:
            dest_key = crc(v)
            buff += s % (src_key, dest_key)
    return tmpl % (style_buff, buff)


def get_countries(filter_countries=None, order='posts'):
    ''' Fetch regional member pages from members title page
        RETURNS:
        tuple (name, url) where:
          - name is a country name
          - url is  a link to page(top50) with users from this country
            ordered by 'posted' by default
    '''
    resp, content = _http.request(
        "%s/community/members/location/" % SITE_ADDR, "GET")

    if resp.status != 200:
       sys.exit("Can't fetch locations: %s" % resp)

    tree = _parse(content)

    locations = tree.xpath('//select[@name = "countries"]/option/@value')

    if filter_countries:
        locations = [loc for loc in locations if filter_countries in loc]

    if not locations:
        sys.exit("Can't find locations: %s" % content)

    for u in locations:
        prefix, country = u.split('=')
        yield (country,
               '%s%s=%s&order=%s' % (SITE_ADDR,
                                     prefix,
                                     quote(country),
                                     order))


def get_country_top50_users(country_url):
    ''' Fetch first page of users by for country.
        RETURNS:
        tuple (name, url) where:
          - name is a name of user
          - url is an url of user's page
    '''

    resp, content = _http.request(country_url, "GET")
    if resp.status != 200:
       sys.exit("Can't fetch users from url: %s" % country_url)

    tree = _parse(content)
    users = tree.xpath('//div[@class="userinfo"]/p[@class="uname"]/b/a')
    if not users:
        sys.exit("Can't fetch users id's for %s" % country_url)

    for u in users:
        href = u.attrib['href'].decode('utf-8')
        login = unquote(href.split('/')[-2])
        name = '%s(%s)' % (u.text, login)

        yield (name, '%s%s' % (SITE_ADDR, href))


def get_friends_of_user(user_url):
    ''' Fethc first page of user's friends
        RETURNS:
          - name is a name of user
          - url is an url of user's page
    '''
    resp, content = _http.request('%sfriends/' % user_url, "GET")
    if resp.status != 200:
       sys.exit("Can't fetch users from url: %s" % user_url)

    tree = _parse(content)
    friends = tree.xpath('//div[@id="myfriends"]/ul/li/div/a')
    if not friends:
        #print "Can't fetch friends id's for %s" % user_url
        raise StopIteration

    for f in friends:
        href = f.attrib['href'].decode('utf-8')
        login = unquote(href.split('/')[-2])
        name = '%s(%s)' % (f.find('b').text, login)

        yield (name, '%s%s' % (SITE_ADDR, href))


def get_user_by_login(login):

    ''' Fetch username by login '''

    url = '%s/%s/' % (SITE_ADDR, quote(login))
    url_blog = '%s/%s/blog/' % (SITE_ADDR, quote(login))
    resp, content = _http.request(url_blog, "GET")
    if resp.status != 200:
       sys.exit("Can't fetch user page for: %s" % url_blog)

    tree = _parse(content)
    username = tree.xpath('//div[@id="qp"]/h2/text()')
    if not username:
        return (None, url)
    else:
        return (username[0], url)


def get_foaf_of_users(logins,
                      timeout=5,
                      mutual_friends_only=False):
    ''' Build FOAF graph for all users '''
    foaf = {}
    for login in logins:
        username, user_url = get_user_by_login(login)
        if not username:
            print "Can't get user info for %s" % login
            continue
        if username in foaf:
            continue

        print '\t"%s" (%s)' % (username, user_url)

        friends = list(get_friends_of_user(user_url))
        foaf[username] = [f_name for f_name, f_url in friends]
        for friendname, friend_url in friends:
            print '\t\t"%s" (%s)' % (friendname, friend_url)
            # friends of a friend
            if friendname in foaf:
                continue
            foaf[friendname] = []
            for ffriend_name, ffriend_url in get_friends_of_user(friend_url):
                print '\t\t\t"%s" (%s)' % (ffriend_name, ffriend_url)
                if mutual_friends_only and (ffriend_name not in foaf[username]):
                    continue
                if ffriend_name not in foaf:
                    foaf[ffriend_name] = []
                foaf[friendname].append(ffriend_name)
            # wait for a while
            sleep(timeout)
        # wait for a while
        sleep(timeout)
    return foaf

if __name__ == '__main__':
    # test
    print get_foaf_of_users([sys.argv[1],], timeout=2)
