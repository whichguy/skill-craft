"""Local record store. Library and JSON CLI share the checked public operations."""
import argparse
import json
from pathlib import Path

class Store:
    def __init__(self):
        self.values = {}
        self.revision = 0

    def apply(self, action, key='sample', value=None):
        if action == 'create':
            if key in self.values:
                return {'error': 'AlreadyExists', 'revision': self.revision}
            self.values[key] = value
        elif action in ('update', 'get', 'delete'):
            if key not in self.values:
                return {'error': 'NotFound', 'revision': self.revision}
            if action == 'get':
                return {'value': self.values[key], 'revision': self.revision}
            if action == 'update':
                self.values[key] = value
            else:
                del self.values[key]
        elif action == 'clear':
            self.values.clear()
        else:
            raise ValueError(action)
        self.revision += 1
        return {'value': self.values.get(key), 'revision': self.revision}

    def apply_unchecked(self, action, key='sample', value=None):
        """State-writing helper; deliberately does not validate operation preconditions."""
        if action in ('create', 'update'):
            self.values[key] = value
        elif action == 'delete':
            self.values.pop(key, None)
        elif action == 'clear':
            self.values.clear()
        elif action == 'get':
            return {'value': self.values.get(key), 'revision': self.revision}
        else:
            raise ValueError(action)
        self.revision += 1
        return {'value': self.values.get(key), 'revision': self.revision}

    def setup(self, config):
        self.values = {}
        self.revision = 0
        self.apply('create', 'sample', 'draft')
        if config['clear_on_start']:
            self.apply('clear')
        return {'keys': sorted(self.values), 'revision': self.revision}


def main():
    p = argparse.ArgumentParser(__doc__)
    p.add_argument('--file', default='session.json')
    p.add_argument('action', choices=['setup', 'create', 'get', 'update', 'delete', 'clear', 'smoke'])
    p.add_argument('key', nargs='?', default='sample')
    p.add_argument('value', nargs='?')
    args = p.parse_args()
    if args.action == 'smoke':
        s = Store()
        assert s.apply('update')['error'] == 'NotFound'
        s.apply('create', 'a', 'one')
        assert s.apply('update', 'a', 'two')['value'] == 'two'
        assert s.apply('get', 'a')['value'] == 'two'
        print('checked library and CLI import smoke: passed')
        return
    path = Path(args.file)
    s = Store()
    if path.exists():
        d = json.loads(path.read_text())
        s.values, s.revision = d['values'], d['revision']
    out = s.setup(json.loads(Path('setup.json').read_text())) if args.action == 'setup' else s.apply(args.action, args.key, args.value)
    path.write_text(json.dumps({'values': s.values, 'revision': s.revision}) + '\n')
    print(json.dumps(out, sort_keys=True))

if __name__ == '__main__':
    main()
