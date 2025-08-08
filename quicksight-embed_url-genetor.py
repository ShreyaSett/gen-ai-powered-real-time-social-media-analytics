import json
import boto3
from botocore.exceptions import ClientError

print(f"Boto3 Version: {boto3.__version__}")

def lambda_handler(event, context):
    # Configure CORS
    headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type",
        "Access-Control-Allow-Methods": "OPTIONS,POST,GET"
    }
    
    # Handle preflight OPTIONS request
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps('Preflight request successful')
        }
    
    try:
        # Initialize QuickSight client
        quicksight = boto3.client('quicksight')
        
        # Replace with your AWS account ID
        aws_account_id = '791778419401'
        
        # Replace with your allowed domains
        allowed_domains = [
            'http://localhost:8501',
            'https://localhost:8501'
        ]
        
        # User ARN
        user_arn = f'arn:aws:quicksight:us-east-1:{aws_account_id}:user/default/Admin/issett-Isengard'
        
        print(f"Generating embed URL for user: {user_arn}")
        
        # Generate embed URL for registered user with QuickSight Console experience only
        response = quicksight.generate_embed_url_for_registered_user(
            AwsAccountId=aws_account_id,
            UserArn=user_arn,
            ExperienceConfiguration={
                'Dashboard': {
                    'InitialDashboardId': '9998cf6d-60dd-43bf-ae34-71a7cc4cccb7',
                    'FeatureConfigurations': {
                        'StatePersistence': {
                            'Enabled': True
                        },
                        'SharedView': {
                            'Enabled': True
                        },
                        'Bookmarks': {
                            'Enabled': True
                        },
                        'AmazonQInQuickSight': {
                            'ExecutiveSummary': {
                                'Enabled': True
                            }
                        },
                        'Schedules': {
                            'Enabled': True
                        },
                        'RecentSnapshots': {
                            'Enabled': True
                        },
                        'ThresholdAlerts': {
                            'Enabled': True
                        }
                    }
                }
            },
            AllowedDomains=allowed_domains,
            SessionLifetimeInMinutes=600
        )

        embed_url = response['EmbedUrl']
        request_id = response['RequestId']
        
        print(f"Embed URL generated successfully. Request ID: {request_id}")
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'embedUrl': embed_url,
                'requestId': request_id,
                'buildVisual': True
            })
        }
    
    except ClientError as e:
        print(f"ClientError: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({
                'error': str(e),
                'errorType': 'ClientError'
            })
        }
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({
                'error': str(e),
                'errorType': type(e).__name__
            })
        }
