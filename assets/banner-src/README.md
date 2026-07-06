# Banner source

HyperFrames composition that renders `assets/banner.gif` / `assets/banner.mp4`.

Rebuild:

```bash
npx hyperframes render assets/banner-src -o banner.mp4
ffmpeg -i banner.mp4 -vf "fps=12,palettegen=max_colors=128:stats_mode=diff" palette.png
ffmpeg -i banner.mp4 -i palette.png -lavfi "fps=12[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=4:diff_mode=rectangle" assets/banner.gif
```
