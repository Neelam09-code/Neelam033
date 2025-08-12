const express = require('express');
const ytdl = require('ytdl-core');
const path = require('path');
const cors = require('cors');

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));
app.use(express.static('public'));

// Serve the main page
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

// Get video info
app.post('/api/video-info', async (req, res) => {
    try {
        const { url } = req.body;
        
        if (!url) {
            return res.status(400).json({ error: 'URL is required' });
        }

        if (!ytdl.validateURL(url)) {
            return res.status(400).json({ error: 'Invalid YouTube URL' });
        }

        const info = await ytdl.getInfo(url);
        const videoDetails = info.videoDetails;
        
        // Get available formats
        const formats = ytdl.filterFormats(info.formats, 'videoandaudio');
        const audioFormats = ytdl.filterFormats(info.formats, 'audioonly');
        
        const availableFormats = [
            ...formats.map(format => ({
                itag: format.itag,
                quality: format.qualityLabel || format.quality,
                container: format.container,
                hasVideo: format.hasVideo,
                hasAudio: format.hasAudio,
                filesize: format.contentLength
            })),
            ...audioFormats.slice(0, 2).map(format => ({
                itag: format.itag,
                quality: 'Audio Only',
                container: format.container,
                hasVideo: false,
                hasAudio: format.hasAudio,
                filesize: format.contentLength
            }))
        ];

        res.json({
            title: videoDetails.title,
            thumbnail: videoDetails.thumbnails[videoDetails.thumbnails.length - 1].url,
            uploader: videoDetails.author.name,
            duration: videoDetails.lengthSeconds,
            viewCount: videoDetails.viewCount,
            formats: availableFormats.slice(0, 8) // Limit to 8 formats
        });

    } catch (error) {
        console.error('Error getting video info:', error);
        res.status(500).json({ error: 'Failed to get video information' });
    }
});

// Download video
app.get('/api/download', async (req, res) => {
    try {
        const { url, itag } = req.query;
        
        if (!url || !ytdl.validateURL(url)) {
            return res.status(400).json({ error: 'Invalid YouTube URL' });
        }

        const info = await ytdl.getInfo(url);
        const title = info.videoDetails.title.replace(/[^\w\s]/gi, '');
        
        const format = ytdl.chooseFormat(info.formats, { quality: itag });
        const extension = format.container;
        
        res.header('Content-Disposition', `attachment; filename="${title}.${extension}"`);
        res.header('Content-Type', format.mimeType);
        
        ytdl(url, { quality: itag }).pipe(res);
        
    } catch (error) {
        console.error('Error downloading video:', error);
        res.status(500).json({ error: 'Failed to download video' });
    }
});

app.listen(PORT, () => {
    console.log(`YouTube Downloader server running on port ${PORT}`);
});