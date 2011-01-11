#!/usr/bin/env python
# coding: utf-8

#
# Visualization of FOAF woth GraphViz
#

if __name__ == "__main__":
    from subprocess import call
    from datetime import datetime
    import sys
    import os

    import graph

    if len(sys.argv) < 2:
        sys.exit('Usage: %s <country name>' % sys.argv[0])

    login = sys.argv[1]

    try:
        retcode = call('which circo > /dev/null 2>&1', shell=True)
        if retcode != 0:
            sys.exit('Unable to locate `circo`')
    except OSError, e:
        sys.exit('Execution failed: %s' % e)

    if not os.path.isdir('_data'):
        os.mkdir('_data')

    # Get the FOAF
    foaf = graph.get_foaf_of_users([login,], timeout=1,
                                   mutual_friends_only=True)
    dot_str = graph.graph2dot(foaf)

    f_name = datetime.now().strftime('%Y-%m-%d_%H%S')

    with open('_data/%s.dot' % f_name, 'w') as dot_file:
        dot_file.write(dot_str.encode('utf-8'))

    cmd = 'circo -Tsvg _data/%s.dot > _data/%s.svg'
    try:
        retcode = call(cmd % (f_name, f_name), shell=True)
        if retcode != 0:
            sys.exit('circo fails')
    except OSError, e:
        sys.exit('Execution failed: %s' % e)
