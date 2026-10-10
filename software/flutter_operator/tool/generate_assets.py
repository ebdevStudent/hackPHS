"""Reproducible app marks and a labelled camera test card; no aircraft imagery."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
ROOT = Path(__file__).resolve().parents[1]

def mark(size):
    image = Image.new('RGBA', (size, size), '#f6f7f4')
    d = ImageDraw.Draw(image)
    inset = size * .18
    width = max(2, int(size * .045))
    d.ellipse((inset,inset,size-inset,size-inset), outline='#295d4d',width=width)
    d.ellipse((size*.36,inset,size*.64,size-inset), outline='#295d4d',width=max(2,width//2))
    d.ellipse((inset,size*.36,size-inset,size*.64), outline='#295d4d',width=max(2,width//2))
    return image

if __name__ == '__main__':
    for folder in ['web/icons','assets/fixtures']:
        (ROOT/folder).mkdir(parents=True, exist_ok=True)
    mark(32).save(ROOT/'web/favicon.png')
    for size in (192,512):
        for prefix in ('Icon','Icon-maskable'):
            mark(size).convert('RGB').save(ROOT/f'web/icons/{prefix}-{size}.png')
    for density,size in [('mdpi',48),('hdpi',72),('xhdpi',96),('xxhdpi',144),('xxxhdpi',192)]:
        path = ROOT/f'android/app/src/main/res/mipmap-{density}/ic_launcher.png'
        path.parent.mkdir(parents=True, exist_ok=True)
        mark(size).save(path)
    for path in (ROOT/'macos/Runner/Assets.xcassets/AppIcon.appiconset').glob('app_icon_*.png'):
        size=int(path.stem.split('_')[-1])
        mark(size).save(path)
    image=Image.new('RGB',(1280,720),'#29362f')
    draw=ImageDraw.Draw(image)
    for x in range(0,1280,80): draw.line((x,0,x,720),fill='#35443b',width=1)
    for y in range(0,720,80): draw.line((0,y,1280,y),fill='#35443b',width=1)
    for x,y,size,seed in [(448,216,180,7),(845,288,130,12)]:
        draw.rectangle((x,y,x+size,y+size), fill='#e9e9dc')
        unit=size/10
        for row in range(8):
            for col in range(8):
                border=row in (0,7) or col in (0,7)
                dark=border or ((row*19+col*13+seed*7)%11<5)
                if dark:
                    x0=x+unit*(col+1); y0=y+unit*(row+1)
                    draw.rectangle((int(x0),int(y0),int(x0+unit),int(y0+unit)),fill='#1b211d')
    draw.line((620,360,660,360),fill='#516355',width=1)
    draw.line((640,340,640,380),fill='#516355',width=1)
    font=ImageFont.truetype(str(ROOT/'assets/fonts/Inter.ttf'),16)
    draw.text((28,675),'UI fixture · no camera attached',font=font,fill='#afbeb3')
    image.save(ROOT/'assets/fixtures/camera_test_card.png')
