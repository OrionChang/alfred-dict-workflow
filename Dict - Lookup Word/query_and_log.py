#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import sys
import time
import cndict
import json

from cache import Cache
from feedback import Feedback
from alfredplist import AlfredPlist


def query(dictionary, word):
    global config, dict_cache

    enable_cache = config['cache']['enable'] if config else True
    if enable_cache:
        cache_expire = (config['cache']['expire'] if config else 24) * 3600
        now = time.time()

        # dict_cache.set('last lookup time', now, float('inf'))
        # time.sleep(1)
        # if dict_cache.get('last lookup time') != now:
        #     return

        clean_time = dict_cache.get('last clean time')
        if clean_time is None or now - clean_time > cache_expire:
            dict_cache.set('last clean time', now, float('inf'))
            dict_cache.clean_expired()

        cache_name = '{}@{}'.format(word, dictionary)
        cache = dict_cache.get(cache_name)
        if cache:
            return cache

    options = config['options'] if config else {}
    dict_name = cndict.get_full_name(dictionary)
    options = options.get(dict_name, {})

    result = cndict.lookup(dictionary, word, **options)
    if result:
        result = [item.decode('utf-8') for item in result]
        if enable_cache:
            dict_cache.set(cache_name, result, cache_expire)
        return result


feedback = Feedback()
plist = AlfredPlist()
plist.read(os.path.abspath('./info.plist'))
base_dir = os.path.expanduser('~/Library/Caches/com.runningwithcrayons.Alfred-2/Workflow Data/')
dict_cache = Cache(os.path.join(base_dir, plist.get_bundleid()))

try:
    config_data = open(os.path.abspath('./config.json')).read()
    config = json.loads(re.sub(r'//.*', '', config_data))
except:
    config = {}

sys.argv = [arg for arg in sys.argv if arg != '']
argc = len(sys.argv)
if argc == 1:
    feedback.add_item(title=u'Dict - Lookup Word',
                      subtitle=u'Format: "word @ dict". Available dicts are "nj", "ld", "yd", "cb", "bd", "by", "hc".',
                      valid=False)
elif argc == 2:
    arg = sys.argv[1]
    pos = arg.rfind('@')
    if pos == -1:
        word = arg.strip()
        dictionary = config['default'] if config else 'nj'
    else:
        word = arg[:pos].strip()
        dictionary = arg[pos+1:].strip()
        if dictionary == '':
            dictionary = config['default'] if config else 'nj'

    if word == ':':
        internal_cmds = {
            'clean': 'Clean cache',
            'config': 'Edit config file',
            'update': 'Update config'
        }
        feedback.add_item(title='Internal commands',
                          subtitle=u'Press "↩" to execute selected internal command',
                          valid=False)
        for cmd, desc in internal_cmds.iteritems():
            feedback.add_item(title=cmd, subtitle=desc,
                              arg=':{}'.format(cmd), valid=True)
    else:
        arg = u'{} @ {}'.format(word.decode('utf-8'), dictionary.decode('utf-8'))
        try:
            result = query(dictionary, word)
            if result:
                action = config['keymap']['none'] if config else 'open'
                feedback.add_item(title=result[0],
                                  subtitle=u'Press "↩" to {} or "⌘/⌥/⌃/⇧/fn + ↩" to lookup word in other dicts.'.format(
                                           'view full definition' if action == 'open' else 'pronounce word'),
                                  arg=arg, valid=True)
                #   save to a log
                log = word.encode('utf-8').lower() + "@" + result[0].encode('utf-8').replace(word, "", 1).replace(" /", "/", 1)

                for item in result[1:]:
                    feedback.add_item(title=item, arg=u'{} | {}'.format(arg, item), valid=True)
                    #   save to a log
                    log += "<br>" + item.encode('utf-8')

                #   save to a log
                #   discard log if word length is less than 4
                if len(word)>3:
                    path = "~/Documents/Alfred\ Dict\ Logs/log-" + time.strftime("%d-%m-%Y") +  '.txt'
                    shell_command = 'd="' + log + '" && echo "${d}" >> ' + path

                    os.environ['LANG'] = 'en_US.UTF-8'
                    os.system(shell_command)

            else:
                feedback.add_item(title='Dict - Lookup Word',
                                  subtitle=u'Word "{}" doesn\'t exist in dict "{}".'.format(
                                           word.decode('utf-8'), dictionary.decode('utf-8')),
                                  arg=arg, valid=True)
        except cndict.DictLookupError, e:
            feedback.add_item(title=word, subtitle='Error: {}'.format(e), arg=arg, valid=True)
else:
    sys.exit(1)
feedback.output()
