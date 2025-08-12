import os
import json
import tempfile
from django.shortcuts import render
from django.http import JsonResponse, HttpResponse, Http404
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import yt_dlp
from urllib.parse import urlparse, parse_qs


def home(request):
    """Render the home page with the download form."""
    return render(request, 'downloader/home.html')


@csrf_exempt
def get_video_info(request):
    """Get video information without downloading."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        url = data.get('url', '').strip()
        
        if not url:
            return JsonResponse({'error': 'URL is required'}, status=400)
        
        # Validate YouTube URL
        if not is_valid_youtube_url(url):
            return JsonResponse({'error': 'Please enter a valid YouTube URL'}, status=400)
        
        # Configure yt-dlp options for info extraction
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(url, download=False)
                
                # Get available formats
                formats = []
                if 'formats' in info:
                    for f in info['formats']:
                        if f.get('vcodec') != 'none' and f.get('acodec') != 'none':  # Video with audio
                            formats.append({
                                'format_id': f.get('format_id'),
                                'ext': f.get('ext'),
                                'resolution': f.get('height', 'Unknown'),
                                'filesize': f.get('filesize'),
                                'quality': f.get('format_note', 'Unknown')
                            })
                
                # Sort formats by resolution (highest first)
                formats.sort(key=lambda x: x['resolution'] if isinstance(x['resolution'], int) else 0, reverse=True)
                
                video_info = {
                    'title': info.get('title', 'Unknown'),
                    'duration': info.get('duration', 0),
                    'thumbnail': info.get('thumbnail', ''),
                    'uploader': info.get('uploader', 'Unknown'),
                    'view_count': info.get('view_count', 0),
                    'formats': formats[:10]  # Limit to top 10 formats
                }
                
                return JsonResponse({'success': True, 'info': video_info})
                
            except Exception as e:
                return JsonResponse({'error': f'Failed to extract video info: {str(e)}'}, status=400)
                
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'An error occurred: {str(e)}'}, status=500)


@csrf_exempt
def download_video(request):
    """Download the video with specified quality."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        url = data.get('url', '').strip()
        format_id = data.get('format_id', 'best')
        
        if not url:
            return JsonResponse({'error': 'URL is required'}, status=400)
        
        if not is_valid_youtube_url(url):
            return JsonResponse({'error': 'Please enter a valid YouTube URL'}, status=400)
        
        # Create temporary directory for download
        temp_dir = tempfile.mkdtemp()
        
        # Configure yt-dlp options
        ydl_opts = {
            'format': format_id if format_id != 'best' else 'best[height<=720]',
            'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                # Extract info first to get the filename
                info = ydl.extract_info(url, download=False)
                title = info.get('title', 'video')
                
                # Download the video
                ydl.download([url])
                
                # Find the downloaded file
                downloaded_files = os.listdir(temp_dir)
                if not downloaded_files:
                    return JsonResponse({'error': 'Download failed - no file created'}, status=500)
                
                file_path = os.path.join(temp_dir, downloaded_files[0])
                
                # Read file content
                with open(file_path, 'rb') as f:
                    file_content = f.read()
                
                # Clean up temp directory
                try:
                    os.remove(file_path)
                    os.rmdir(temp_dir)
                except:
                    pass
                
                # Return file as download
                response = HttpResponse(file_content, content_type='application/octet-stream')
                response['Content-Disposition'] = f'attachment; filename="{title}.mp4"'
                return response
                
            except Exception as e:
                # Clean up temp directory on error
                try:
                    for file in os.listdir(temp_dir):
                        os.remove(os.path.join(temp_dir, file))
                    os.rmdir(temp_dir)
                except:
                    pass
                return JsonResponse({'error': f'Download failed: {str(e)}'}, status=500)
                
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'An error occurred: {str(e)}'}, status=500)


def is_valid_youtube_url(url):
    """Check if the URL is a valid YouTube URL."""
    parsed_url = urlparse(url)
    
    # Check for various YouTube URL formats
    if parsed_url.netloc in ['www.youtube.com', 'youtube.com', 'm.youtube.com']:
        return True
    elif parsed_url.netloc in ['youtu.be']:
        return True
    
    return False