import sys
content = open('frontend/src/App.tsx').read()
target = '''<div className="text-[10px] text-slate-500 font-mono mt-0.5">
                  Vision Transformer (ViT)
                </div>'''
replacement = '''<div className="text-[10px] text-slate-500 font-mono mt-0.5 flex items-center gap-2">
                  Vision Transformer (ViT)
                  {metadata && (
                    <DataSourceBadge 
                      dataSource={metadata.data_source || 'mock'} 
                      modelVersion={metadata.model_version || 'unknown'} 
                    />
                  )}
                </div>'''
if target in content:
    open('frontend/src/App.tsx', 'w').write(content.replace(target, replacement))
    print('Success')
else:
    print('Not found')
