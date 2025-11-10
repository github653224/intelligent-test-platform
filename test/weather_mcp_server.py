import json 
import asyncio
import httpx
from typing import Dict, Any
from mcp.server.fastmcp import FastMCP 


mcp = FastMCP("weather-mcp-server")

OPENWEATHER_API_BASE = "https://api.openweathermap.org/data/2.5/weather"
OPENWEATHER_API_KEY = "2986e20c6e034b338e42a97b546d6523"
USER_AGENT = "weather-app/1.0"

async def get_weather(city: str) -> Dict[str, Any]:
    params = {
        "q": city,
        "appid": OPENWEATHER_API_KEY,
        "units": "metric",
        "lang": "zh_cn",
    }
    
    headers = {
        "User-Agent": USER_AGENT,
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(OPENWEATHER_API_BASE, params=params, headers=headers)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise Exception(f"HTTP error: {e}")
        except Exception as e:
            raise Exception(f"Error getting weather: {e}")


if __name__ == "__main__":
    # 输出天气信息
    weather = asyncio.run(get_weather("Beijing"))
    print(json.dumps(weather, indent=2, ensure_ascii=False))
    

