def load_properties(filepath):
    props = {}
    with open(filepath, 'r') as f:
        for line in f:
            if '=' in line:
                key, value = line.strip().split('=', 1)
                props[key.strip()] = value.strip()
    return props
