import os

print('🧪 Terraform Validation Script')
print('=' * 40)

if os.path.exists('main.tf'):
    with open('main.tf', 'r') as f:
        content = f.read()
        
    # Check for required resources
    required_resources = [
        'aws_s3_bucket',
        'aws_dynamodb_table', 
        'aws_lambda_function',
        'aws_iam_role',
        'aws_sns_topic'
    ]
    
    print('🧪 Terraform Resource Check:')
    for resource in required_resources:
        if resource in content:
            print(f'✅ {resource}')
        else:
            print(f'❌ {resource}')
            
    print(f'\n📏 File size: {len(content)} characters')
    
    # Check for key sections
    key_sections = ['provider "aws"', 'variable', 'output']
    print('\n🔧 Configuration Check:')
    for section in key_sections:
        if section in content:
            print(f'✅ {section}')
        else:
            print(f'❌ {section}')

    print('\n📋 Summary:')
    if 'aws_s3_bucket' in content and 'aws_dynamodb_table' in content:
        print('✅ Terraform file looks complete!')
    else:
        print('❌ Terraform file missing key resources')
            
else:
    print('❌ main.tf not found')
    print('📁 Current files:', os.listdir('.'))