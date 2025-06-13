import os

print('Checking GitHub Actions file...')

# Check if file exists
if os.path.exists('../.github/workflows/deploy.yml'):
    print('GitHub Actions file found')
    try:
        with open('../.github/workflows/deploy.yml', 'r', encoding='utf-8') as f:
            content = f.read()
            if 'Deploy Energy Data Pipeline' in content:
                print('Content looks correct')
                print(f'File size: {len(content)} characters')
            else:
                print('Content might be wrong')
    except UnicodeDecodeError:
        print('File has encoding issues - fixing...')
        # Try to read and fix encoding
        with open('../.github/workflows/deploy.yml', 'rb') as f:
            raw_content = f.read()
        
        # Write back with proper encoding
        with open('../.github/workflows/deploy.yml', 'w', encoding='utf-8') as f:
            f.write(raw_content.decode('utf-8', errors='replace'))
        
        print('File encoding fixed')
else:
    print('GitHub Actions file not found')
    print('Current directory:', os.getcwd())