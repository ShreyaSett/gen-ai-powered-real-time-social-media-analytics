import boto3
import json
import os
import datetime
import logging
import hashlib
import base64
import re
import time
import random
import traceback
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Simple in-memory cache
response_cache = {}

def validate_environment():
    """Validate required environment variables"""
    required_vars = [
        'OPENSEARCH_ENDPOINT',
        'USER_EMBEDDINGS_INDEX',
        'KB_EMBEDDINGS_INDEX',
        'OUTPUT_S3_BUCKET'
    ]
    
    for var in required_vars:
        value = os.environ.get(var)
        if not value:
            raise Exception(f"Missing required environment variable: {var}")
        if var == 'OUTPUT_S3_BUCKET':
            try:
                s3_client = boto3.client('s3')
                s3_client.head_bucket(Bucket=value)
            except Exception as e:
                raise Exception(f"S3 bucket validation failed: {str(e)}")

def get_from_cache(key):
    """Get a response from the cache if it exists and is not expired"""
    if key in response_cache:
        entry = response_cache[key]
        if entry['expiry'] > datetime.datetime.now().timestamp():
            logger.info(f"Cache hit for key: {key}")
            return entry['data']
    return None

def store_in_cache(key, data, ttl=3600):
    """Store a response in the cache with an expiry time"""
    expiry = datetime.datetime.now().timestamp() + ttl
    response_cache[key] = {
        'data': data,
        'expiry': expiry
    }
    logger.info(f"Stored in cache: {key}")

import json
import boto3

def generate_video_with_nova(text, s3_bucket):
    """Generate video using Nova Reel and store in S3"""
    try:
        # Create the Bedrock Runtime client.
        bedrock_runtime = boto3.client("bedrock-runtime")

        # Create unique folder for this generation
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        folder_path = f"nova-videos/{timestamp}"
        s3_uri = f"s3://{s3_bucket}/{folder_path}/"

        model_input = {
            "taskType": "TEXT_VIDEO",
            "textToVideoParams": {
                "text": text
            },
            "videoGenerationConfig": {
                "durationSeconds": 6,
                "fps": 24,
                "dimension": "1280x720",
                "seed": 0,  # Change the seed to get a different result
            },
        }

        # Start the asynchronous video generation job.
        invocation = bedrock_runtime.start_async_invoke(
            modelId="amazon.nova-reel-v1:1",
            modelInput=model_input,
            outputDataConfig={
                "s3OutputDataConfig": {
                    "s3Uri": s3_uri
                }
            }
        )

        # Print the response JSON.
        print("Response:")
        print(json.dumps(invocation, indent=2, default=str))

        return {
            'success': True,
            'invocation': invocation
        }

    except Exception as e:
        # Implement error handling here.
        message = e.response["Error"]["Message"]
        print(f"Error: {message}")
        return {
            'success': False,
            'error': message
        }


def lambda_handler(event, context):
    try:
        # Log the entire event for debugging
        logger.info(f"Received event: {json.dumps(event)}")
        
        # Validate environment variables
        validate_environment()
        
        # Parse the input from API Gateway
        if 'body' in event:
            if isinstance(event['body'], str):
                try:
                    body = json.loads(event['body'])
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse body as JSON: {event['body']}")
                    return {
                        'statusCode': 400,
                        'headers': {
                            'Content-Type': 'application/json',
                            'Access-Control-Allow-Origin': '*'
                        },
                        'body': json.dumps({'error': 'Invalid JSON in request body'})
                    }
            else:
                body = event['body']
        else:
            body = event
        
        logger.info(f"Parsed body: {json.dumps(body)}")
        
        # Extract the query
        user_query = None
        if isinstance(body, dict):
            user_query = body.get('query', '')
        
        logger.info(f"Extracted query: {user_query}")
        
        # Validate the query
        if not user_query:
            logger.error("No query provided or query extraction failed")
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'error': 'No query provided or invalid request format'})
            }

        # Get conversation history if available
        conversation_history = []
        if isinstance(body, dict) and 'conversation_history' in body:
            conversation_history = body.get('conversation_history', [])
        
        # Create cache key
        cache_key = hashlib.md5(
            (user_query + json.dumps(conversation_history)).encode()
        ).hexdigest()
        
        # Check cache first
        cached_response = get_from_cache(cache_key)
        if cached_response:
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps(cached_response)
            }

        # Initialize Bedrock client
        region = os.environ.get('AWS_REGION', 'us-east-1')
        bedrock_runtime = boto3.client('bedrock-runtime', region_name=region)

        # Check if this is a video generation request
        is_video_request = any(phrase in user_query.lower() for phrase in [
            'generate video', 'create video', 'make video',
            'brand video', 'campaign video'
        ])
        
        if is_video_request:
            try:
                # Extract video prompt
                video_prompt = user_query
                if "for" in user_query.lower():
                    video_prompt = user_query.split("for")[-1].strip()
                
                # Clean and enhance the prompt
                video_prompt = video_prompt.strip()
                logger.info(f"Processing video request with prompt: {video_prompt}")

                # Get S3 bucket
                s3_bucket = os.environ.get('OUTPUT_S3_BUCKET')
                if not s3_bucket:
                    raise ValueError("OUTPUT_S3_BUCKET environment variable not set")

                # Generate video
                video_result = generate_video_with_nova(video_prompt, s3_bucket)

                if video_result['success']:
                    response_data = {
                        'type': 'video',
                        'query': user_query,
                        'generated_response': f"✨ Video generation job started successfully!\n\nPrompt: {video_prompt}",
                        'invocation': video_result['invocation']
                    }

                    store_in_cache(cache_key, response_data)

                    return {
                        'statusCode': 200,
                        'headers': {
                            'Content-Type': 'application/json',
                            'Access-Control-Allow-Origin': '*'
                        },
                        'body': json.dumps(response_data)
                    }
                else:
                    error_message = video_result.get('error', 'Unknown error')
                    logger.error(f"Video generation failed: {error_message}")
                    return {
                        'statusCode': 500,
                        'headers': {
                            'Content-Type': 'application/json',
                            'Access-Control-Allow-Origin': '*'
                        },
                        'body': json.dumps({
                            'error': f"Failed to start video generation: {error_message}"
                        })
                    }

            except Exception as e:
                logger.error(f"Error handling video request: {str(e)}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                return {
                    'statusCode': 500,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps({
                        'error': f"Video generation request failed: {str(e)}"
                    })
                }

        # Handle regular text query
        # Get environment variables for OpenSearch
        opensearch_endpoint = os.environ['OPENSEARCH_ENDPOINT']
        user_embeddings_index = os.environ['USER_EMBEDDINGS_INDEX']
        kb_embeddings_index = os.environ['KB_EMBEDDINGS_INDEX']
        model_id = os.environ.get('MODEL_ID', 'anthropic.claude-3-haiku-20240307-v1:0')
        
        # Generate embedding
        request_body = json.dumps({
            "inputText": user_query
        })
        
        logger.info("Calling Bedrock to generate embeddings")
        
        try:
            response = bedrock_runtime.invoke_model(
                modelId="amazon.titan-embed-text-v2:0",
                contentType="application/json",
                accept="application/json",
                body=request_body
            )
            
            response_body = json.loads(response['body'].read())
            user_embedding = response_body['embedding']
            logger.info(f"Successfully generated embedding")
            
        except Exception as e:
            logger.error(f"Error generating embedding: {str(e)}")
            return {
                'statusCode': 500,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'error': f'Error generating embedding: {str(e)}'})
            }
        
        # Connect to OpenSearch
        credentials = boto3.Session().get_credentials()
        awsauth = AWS4Auth(
            credentials.access_key,
            credentials.secret_key,
            region,
            'aoss',
            session_token=credentials.token
        )
        
        opensearch = OpenSearch(
            hosts=[{'host': opensearch_endpoint, 'port': 443}],
            http_auth=awsauth,
            use_ssl=True,
            verify_certs=True,
            connection_class=RequestsHttpConnection
        )
        
        # Store user query embedding
        user_document = {
            'query_text': user_query,
            'bedrock-knowledge-base-default-vector': user_embedding,
            'timestamp': datetime.datetime.now().isoformat()
        }
        
        try:
            opensearch.index(
                index=user_embeddings_index,
                body=user_document
            )
            logger.info(f"Indexed user query to OpenSearch")
        except Exception as e:
            logger.error(f"Error indexing to OpenSearch: {str(e)}")
        
        # Search query
        query = {
            "size": 5,
            "query": {
                "knn": {
                    "bedrock-knowledge-base-default-vector": {
                        "vector": user_embedding,
                        "k": 5
                    }
                }
            },
            "_source": ["AMAZON_BEDROCK_TEXT", "AMAZON_BEDROCK_METADATA", "AMAZON_BEDROCK_TEXT_CHUNK"]
        }
        
        # Execute search
        search_results = opensearch.search(
            index=kb_embeddings_index,
            body=query
        )
        
        # Process results
        hits = search_results['hits']['hits']
        results = []
        context_text = ""
        
        for hit in hits:
            source = hit['_source']
            text = source.get('AMAZON_BEDROCK_TEXT', '') or source.get('AMAZON_BEDROCK_TEXT_CHUNK', '')
            
            results.append({
                'score': hit['_score'],
                'text': text
            })
            
            if text:
                context_text += text + "\n\n"
        
        # Format conversation history
        conversation_context = ""
        if conversation_history:
            conversation_context = "Previous conversation:\n"
            for message in conversation_history[-3:]:
                role = message.get('role', '')
                content = message.get('content', '')
                conversation_context += f"{role}: {content}\n"
            conversation_context += "\n"
        
        # Generate LLM response
        try:
            prompt = f"""
            You are a helpful assistant for AnyCompany, a social media platform. 

            Important Context:
                        1. About AnyCompany:
                        - AnyCompany is EXCLUSIVELY a social media platform
                        - It competes ONLY with other social media platforms (Twitter/X, Facebook, Instagram, TikTok, etc.)
            Special Handling for AnyCompnay Platform Sentiment:
                        If and only if asked about AnyCompany:
                        1. Positive sentiment examples:
                        - Users praising AnyCompany's features
                        - Users preferring AnyCompany over other social platforms
                        - Users reporting better experiences on AnyCompany

                        2. Negative sentiment examples:
                        - Users preferring other platforms over AnyCompany
                        - Complaints about AnyCompany's features
                        - Users reporting better experiences on competitor platforms

                        3. Remember:
                        - If people say other platforms are better = NEGATIVE for AnyCompany
                        - If people say AnyCompany is better = POSITIVE for AnyCompany
                        - If people just mention using other platforms = NEUTRAL

                        {conversation_context}

                        Context:
                        {context_text}

                        User Question: {user_query}

            For all questions answer concisely but thoroughly, using only the information in the context. If the context is insufficient, acknowledge the limitations.

            """
            
            llm_request = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1000,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.7,
                "top_p": 0.9
            }
            
            llm_response = bedrock_runtime.invoke_model(
                modelId=model_id,
                contentType="application/json",
                accept="application/json",
                body=json.dumps(llm_request)
            )
            
            llm_response_body = json.loads(llm_response['body'].read())
            
            if "content" in llm_response_body:
                content_list = llm_response_body.get("content", [])
                if content_list and len(content_list) > 0:
                    first_content = content_list[0]
                    if isinstance(first_content, dict) and "text" in first_content:
                        generated_text = first_content["text"]
                    else:
                        generated_text = str(first_content)
                else:
                    generated_text = "No content in LLM response"
            else:
                logger.error(f"Unexpected response format: {json.dumps(llm_response_body)[:200]}...")
                generated_text = "Error: Unexpected response format from LLM"
            
        except Exception as e:
            logger.error(f"Error generating LLM response: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            
            generated_text = "Sorry, I couldn't generate a response. Here are the relevant results:"
            for result in results:
                text = result.get('text', '')
                if text:
                    generated_text += f"\n\n{text}"
        
        # Prepare response
        response_data = {
            'type': 'text',
            'query': user_query,
            'generated_response': generated_text,
            'citations': results
        }
        
        # Store in cache
        store_in_cache(cache_key, response_data)
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(response_data)
        }

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'error': str(e)})
        }
