import json
import boto3
import urllib.parse
from datetime import datetime

# DynamoDB リソースの設定
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('Reservations')

# 許可されたオリジンのリスト
ALLOWED_ORIGINS = [
    'https://amp.gmail.dev',
    'https://mail.google.com',
    # 必要に応じて他のオリジンを追加
]

def lambda_handler(event, context):
    print("Lambda function started")
    http_method = event.get('httpMethod', '')
    path = event.get('path', '')
    headers = event.get('headers', {})
    origin = headers.get('Origin', '')
    content_type = headers.get('Content-Type', '')

    print(f"Received request: {http_method} {path} from {origin}")

    # オリジンが許可されているかチェック
    if origin in ALLOWED_ORIGINS:
        allowed_origin = origin
    else:
        allowed_origin = ''  # 許可されていないオリジンからのリクエストは処理しない

    # レスポンスのベース
    response = {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': allowed_origin,
            'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Credentials': 'true',
            'Access-Control-Expose-Headers': 'AMP-Access-Control-Allow-Source-Origin',
            'AMP-Access-Control-Allow-Source-Origin': 'amp@gmail.dev'
        },
        'body': ''
    }

    try:
        if http_method == 'OPTIONS':
            # CORS プリフライトリクエストへの対応
            response['statusCode'] = 200
            response['body'] = ''
            print("Handled OPTIONS request")
            return response

        elif http_method == 'POST' and '/submit-reservation' in path:
            # リクエストボディの取得
            body = event.get('body', '')
            print(f"Received Body: {body}")

            if not body:
                response['statusCode'] = 400
                response['body'] = json.dumps({"error": "リクエストボディが空です"})
            else:
                # Content-Type に基づいてボディをパース
                if 'application/json' in content_type:
                    # JSON 形式の場合
                    data = json.loads(body)
                else:
                    # URL エンコード形式の場合
                    data = urllib.parse.parse_qs(body)
                    # 値を取得しやすい形式に変換
                    data = {k: v[0] if isinstance(v, list) else v for k, v in data.items()}

                print(f"Parsed Data: {data}")

                # 必須フィールドの取得
                date_selected = data.get('date')
                child_name = data.get('child_name')
                parent_name = data.get('parent_name')
                parent_email = data.get('parent_email')

                # 必須フィールドの検証
                if not all([date_selected, child_name, parent_name, parent_email]):
                    response['statusCode'] = 400
                    response['body'] = json.dumps({"error": "必須フィールドが不足しています"})
                else:
                    # DynamoDB にデータを保存
                    table.put_item(
                        Item={
                            'parent_email': parent_email,  # パーティションキー
                            'reservation_timestamp': datetime.now().isoformat(),  # ソートキー
                            'date': date_selected,
                            'child_name': child_name,
                            'parent_name': parent_name
                        }
                    )
                    response['body'] = json.dumps({'message': 'Reservation saved successfully!'})

        else:
            # 許可されていないメソッドまたはパスの場合
            response['statusCode'] = 405
            response['body'] = json.dumps({"error": "許可されていないメソッドまたはパスです"})
            print("Method not allowed or path not recognized")

    except Exception as e:
        # エラーハンドリング
        print(f"Error occurred: {str(e)}")
        response['statusCode'] = 500
        response['body'] = json.dumps({"error": f"Exception: {str(e)}"})

    print(f"Response: {response}")
    return response
