from __future__ import print_function, absolute_import
import s


def cover():
    for test_file in s.test.fast_test_files():
        data = s.test._cover(test_file)
        if data:
            text = ''
            text += s.colors.yellow(data['name']) + ' '
            text += getattr(s.colors, 'green' if data['percent'] == '100' else 'red')(data['percent'] + '% ')
            print(text)
            if data['missing']:
                missing_text = ''
                missing_count = 5
                missing_text += (', '.join(data['missing'][:missing_count]) +
                                 ('...' if len(data['missing']) > missing_count else ''))
                print(s.strings.indent(missing_text, 1))
