import re
import sys

def validate(tag, project, sha):
    if not re.fullmatch(r'ci-[A-Za-z0-9_-]{1,64}-[0-9a-f]{40}-[0-9a-f]{8}', tag):
        raise ValueError('Invalid release tag')
    if not tag.startswith('ci-' + project + '-' + sha.lower() + '-'):
        raise ValueError('Release tag does not match commit')
    return tag

if __name__ == '__main__':
    validate(*sys.argv[1:4])
