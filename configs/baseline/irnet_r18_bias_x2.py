_base_ = [
    '../_base_/datasets/imagenet_bs128.py',
    '../_base_/schedules/imagenet_bs1024.py', '../_base_/default_runtime.py'
]

model = dict(
    type='ImageClassifier',
    backbone=dict(
        type='ResArch',
        arch='IRNet-18-bias-x2',
        num_stages=4,
        out_indices=(3, ),
        stem_act='hardtanh',
        style='pytorch'),
    neck=dict(type='GlobalAveragePooling'),
    head=dict(
        type='IRClsHead',
        num_classes=1000,
        in_channels=512,
        loss=dict(type='CrossEntropyLoss', loss_weight=1.0),
        topk=(1, 5),
    ))
custom_imports = dict(imports=['mmcls.core.utils.ede'], allow_failed_imports=False)
custom_hooks = [
    dict(type='EDEHook', total_epoch=100)
]
#work_dir = 'work_dirs/tmp'
work_dir = 'work_dirs/irnet_r18_bias_x2xinference_allgrad'
load_from = 'work_dirs/irnet18_x2x_float/epoch_100.pth'  #加入load_from试试
find_unused_parameters=True
seed = 166
