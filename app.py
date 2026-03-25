from flask import Flask, request, jsonify
import asyncio
import aiohttp
import logging
from typing import Dict, Optional, Tuple

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MultiAPIMerger:
    def __init__(self, api2_key: str = "UDIT"):
        self.apis = [
            {
                "name": "API1",
                "url": "https://stargvhuuvjpy.vercel.app/like",
                "params_template": {"uid": None, "server_name": None}
            },
            {
                "name": "API2", 
                "url": "http://udit-like-api-ffm-20.vercel.app/like",
                "params_template": {"uid": None, "region": None, "key": api2_key}
            }
        ]
    
    async def call_single_api(self, session: aiohttp.ClientSession, 
                              api_config: Dict, uid: str, region: str) -> Tuple[Optional[Dict], str]:
        try:
            params = {}
            for key, value in api_config["params_template"].items():
                if key == "uid":
                    params[key] = uid
                elif key in ["server_name", "region"]:
                    params[key] = region
                elif key == "key":
                    params[key] = value
                else:
                    params[key] = value if value is not None else ""
            
            logger.info(f"Calling {api_config['name']} with params: {params}")
            
            async with session.get(api_config["url"], params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data, api_config["name"]
                else:
                    logger.error(f"{api_config['name']} failed with status {response.status}")
                    return None, api_config["name"]
        except Exception as e:
            logger.error(f"Error calling {api_config['name']}: {e}")
            return None, api_config["name"]
    
    async def merge_multiple_apis(self, uid: str, region: str) -> Dict:
        merged_response = {
            "LikesGivenByAPI": 0,
            "LikesafterCommand": 0,
            "LikesbeforeCommand": 0,
            "PlayerNickname": "N/A",
            "UID": int(uid),
            "status": 2
        }
        
        current_before_value = 0
        total_likes_given = 0
        
        async with aiohttp.ClientSession() as session:
            for i, api_config in enumerate(self.apis):
                response, api_name = await self.call_single_api(session, api_config, uid, region)
                
                if response:
                    likes_before = response.get("LikesbeforeCommand", 0)
                    likes_after = response.get("LikesafterCommand", 0)
                    likes_given_this = likes_after - likes_before
                    total_likes_given += likes_given_this
                    
                    if i == 0:
                        merged_response["LikesbeforeCommand"] = likes_before
                        current_before_value = likes_before
                    
                    if i < len(self.apis) - 1:
                        current_before_value = likes_after
                    else:
                        merged_response["LikesafterCommand"] = likes_after
                    
                    if response.get("PlayerNickname") and response.get("PlayerNickname") != "N/A":
                        merged_response["PlayerNickname"] = response.get("PlayerNickname")
                    
                    if response.get("status") != 2:
                        merged_response["status"] = response.get("status")
                    
                    if response.get("UID"):
                        merged_response["UID"] = response.get("UID")
        
        merged_response["LikesGivenByAPI"] = total_likes_given
        return merged_response

# Create merger instance
merger = MultiAPIMerger(api2_key="UDIT")

@app.route('/merge-likes', methods=['GET'])
def merge_likes():
    """API endpoint to merge likes from all three services"""
    uid = request.args.get('uid')
    region = request.args.get('region', 'ind')  # Default region
    
    if not uid:
        return jsonify({"error": "uid parameter is required"}), 400
    
    try:
        # Run async function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(merger.merge_multiple_apis(uid, region))
        loop.close()
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error processing request: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy"})

if __name__ == '__main__':
    # PORT set karne ke liye environment variable ya direct value
    import os
    
    # Method 1: Environment variable se port lena
    port = int(os.environ.get('PORT', 5000))
    
    # Method 2: Direct port set karna
    # port = 8080  # Apni marzi ka port lagao
    
    # Method 3: Command line argument se port lena
    # import sys
    # port = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    
    print(f"🚀 Server starting on http://localhost:{port}")
    print(f"📡 Endpoint: http://localhost:{port}/merge-likes?uid=YOUR_UID&region=ind")
    print(f"💚 Health check: http://localhost:{port}/health")
    
    app.run(host='0.0.0.0', port=port, debug=True)