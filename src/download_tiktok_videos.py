#working one -download tiktok videos in bulk

import os
import time
import random
import asyncio
import aiohttp
import logging
import pandas as pd
from tqdm import tqdm
import re

# Set up logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.FileHandler("tiktokdownload.log"),
                        logging.StreamHandler()
                    ])

# Configuration
download_directory = 'downloaded_videos3'
batch_size = 50
min_delay = 2
max_delay = 5

if not os.path.exists(download_directory):
    os.makedirs(download_directory)

video_urls = [
'https://www.tiktok.com/@abreezgroup.sa/video/7204830317335645441',
]

async def download_video(session, url):
    try:
        video_id = url.split('/')[-1]
        file_name = f"{video_id}.mp4"
        file_path = os.path.join(download_directory, file_name)
        
        if os.path.exists(file_path):
            logging.info(f"Video {video_id} already exists, skipping.")
            return None

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'https://www.tiktok.com/',
        }

        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                content = await response.text()
                video_url_match = re.search(r'"playAddr":"([^"]+)"', content)
                if video_url_match:
                    video_url = video_url_match.group(1).replace('\\u002F', '/')
                    async with session.get(video_url, headers=headers) as video_response:
                        if video_response.status == 200:
                            with open(file_path, 'wb') as f:
                                f.write(await video_response.read())
                            logging.info(f"Downloaded: {file_path}")
                            return None
                        else:
                            logging.error(f"Failed to download video from {video_url}: HTTP {video_response.status}")
                            return url
                else:
                    logging.error(f"Could not find video URL in the page content for {url}")
                    return url
            else:
                logging.error(f"Failed to fetch page {url}: HTTP {response.status}")
                return url

    except Exception as e:
        logging.error(f"Failed to download {url}: {str(e)}")
        return url

async def process_batch(session, batch):
    failed_urls = []
    tasks = [download_video(session, url) for url in batch]
    for task in tqdm(asyncio.as_completed(tasks), total=len(tasks), desc="Downloading videos"):
        result = await task
        if result:
            failed_urls.append(result)
    return failed_urls

async def main():
    logging.info("Starting main function")
    
    logging.info(f"Processing {len(video_urls)} URLs.")
    all_failed_urls = []
    
    async with aiohttp.ClientSession() as session:
        for i in range(0, len(video_urls), batch_size):
            batch = video_urls[i:i + batch_size]
            logging.info(f"Processing batch {i // batch_size + 1} of {(len(video_urls) + batch_size - 1) // batch_size}")
            
            failed_urls = await process_batch(session, batch)
            all_failed_urls.extend(failed_urls)
            
            # Save failed URLs after each batch
            with open('failed_urls.txt', 'w') as f:
                for url in all_failed_urls:
                    f.write(f"{url}\n")
            
            logging.info(f"Completed batch {i // batch_size + 1}. Total failed: {len(all_failed_urls)}")
            
            # Add a delay between batches
            await asyncio.sleep(random.uniform(min_delay, max_delay))

    logging.info("Download completed. Failed URLs have been saved to 'failed_urls.txt'.")
    
    # Create a DataFrame of failed URLs and save to CSV
    df_failed = pd.DataFrame({'Failed URLs': all_failed_urls})
    df_failed.to_csv('failed_urls.csv', index=False)
    logging.info("Failed URLs have been saved to 'failed_urls.csv'.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.warning("Script interrupted by user. Saving progress...")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {str(e)}")
    finally:
        logging.info("Script execution finished.")