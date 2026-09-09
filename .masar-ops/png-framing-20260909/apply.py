"""Add the reproducer first; apply the runtime fix only after its specific failure is observed."""
from pathlib import Path
import hashlib,sys
root=Path('masar-studio')
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
if sys.argv[1]=='test':
    p=root/'tests/view_controls_browser.py';s=p.read_text()
    assert digest(p)=='a90c89200de2ed99f733ce33a65708fb1b5a217e9f666ba82d435691c6bb38fe'
    needle="with tempfile.TemporaryDirectory(prefix='masar-view-controls-') as tmp:"
    addition='''def check_export_framing(path):
    image=Image.open(path).convert('RGB');footer=60 if image.height==480 else 84
    content=image.crop((0,0,image.width,image.height-footer))
    background=Image.new('RGB',content.size,max(content.getcolors(content.width*content.height),key=lambda item:item[0])[1])
    mask=ImageChops.difference(content,background).convert('L').point(lambda v:255 if v>12 else 0)
    box=mask.getbbox();assert box and box[2]-box[0]>20 and box[3]-box[1]>20,('empty PNG',box)
    assert box[0]>1 and box[1]>1 and box[2]<content.width-1 and box[3]<content.height-1,('wide-camera PNG crops the fitted visible scene',box,content.size)
'''
    assert s.count(needle)==1;s=s.replace(needle,addition+needle)
    needle="                        image=OUT/f'chalet-{width}-{preset}.png';capture_frame(canvas,image);check_image_framing(image,float(canvas.evaluate('e=>parseFloat(getComputedStyle(e).borderTopLeftRadius)||0')))"
    addition='''
                        if width==1280 and preset=='east':
                            wide=download('#render-save-png','wide-camera.png');check_export_framing(wide)
                            passed('fixed-size PNG preserves a wide fitted view without cropping or stretching it')'''
    assert s.count(needle)==1;s=s.replace(needle,needle+addition);p.write_text(s);compile(s,str(p),'exec')
    assert digest(p)=='1ac6c9b8f19dd889e70756d6d4e28fa3d9f6a259b9838be19a1c48fd3bfa1f81'
elif sys.argv[1]=='runtime':
    p=root/'src/three-viewer.mjs';s=p.read_text()
    assert digest(p)=='b1c0cb2902c8ea1f62165f50b97ffa936c000238e20f13953132b3a97a3f8b3e'
    old='''                renderer.setPixelRatio(1);renderer.setSize(width,height-footer,false);camera.aspect=width/(height-footer);camera.updateProjectionMatrix();renderer.render(scene,camera);
                // Copy pixels before WebGL clears the buffer, without preserveDrawingBuffer.
                ctx.drawImage(canvas,0,0,width,height-footer);'''
    new='''                // Preserve the on-screen framing when a fixed PNG has a different aspect.
                // Letterboxing avoids narrowing a wide fitted view or stretching the model.
                const available=height-footer;
                let captureWidth=width,captureHeight=Math.max(1,Math.round(width/oldAspect));
                if(captureHeight>available){captureHeight=available;captureWidth=Math.max(1,Math.round(available*oldAspect));}
                const left=Math.floor((width-captureWidth)/2),top=Math.floor((available-captureHeight)/2);
                renderer.setPixelRatio(1);renderer.setSize(captureWidth,captureHeight,false);camera.aspect=captureWidth/captureHeight;camera.updateProjectionMatrix();renderer.render(scene,camera);
                ctx.fillStyle='#e4e7e8';ctx.fillRect(0,0,width,available);
                // Copy pixels before WebGL clears the buffer, without preserveDrawingBuffer.
                ctx.drawImage(canvas,left,top,captureWidth,captureHeight);'''
    assert s.count(old)==1;p.write_text(s.replace(old,new))
    assert digest(p)=='591d891d38c6e0374ca9fb84f646504d9fe228ced4994d21f55820da5b0330da'
    p=root/'public/sw.js';s=p.read_text()
    assert digest(p)=='3ff61049564455b28bc5f5f761858589cc2cf65f11130bcefd7733ee4ce717cb'
    old='masar-4.1.0-shell-v10-view-controls';assert s.count(old)==1
    p.write_text(s.replace(old,'masar-4.1.0-shell-v11-png-framing'))
    assert digest(p)=='52c6a1d7ca5f0c1ab3260c5b3eee6d19b73e66683ad837361792866ca2e88fee'
else:raise ValueError('Expected test or runtime mode')
print('Applied guarded '+sys.argv[1]+' changes')
