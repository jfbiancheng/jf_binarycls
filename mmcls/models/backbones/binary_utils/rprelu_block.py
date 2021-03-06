import torch
import torch.nn as nn
from .binary_convs import IRConv2dnew, RAConv2d ,IRConv2d_bias ,IRConv2d_bias_x2,IRConv2d_bias_x2x,BLConv2d,StrongBaselineConv2d
from .binary_functions import RPRelu, LearnableBias, LearnableScale, AttentionScale,Expandx,GPRPRelu,MGPRPRelu,GPLearnableBias,scalebias,biasadd,biasadd22,biasaddtry
from .bias_conv import FLRAConv2d
class RPStrongBaselineBlock(nn.Module):
    """Strong baseline block from real-to-binary net"""
    expansion = 1

    def __init__(self, in_channels, out_channels, stride=1, downsample=None, Expand_num=1,rpgroup=1,**kwargs):
        super(RPStrongBaselineBlock, self).__init__()

        if rpgroup == 1:
            self.rpmode = 1
        elif rpgroup == 2:
            self.rpmode = out_channels
        self.bn1 = nn.BatchNorm2d(in_channels)
        self.conv1 = BLConv2d(in_channels, out_channels, kernel_size=3, stride=stride, padding=1, bias=False, **kwargs)
        self.scale1 = LearnableScale(out_channels)
        self.nonlinear1 = RPRelu(self.rpmode)
        self.bn2 = nn.BatchNorm2d(out_channels)
        self.conv2 = BLConv2d(out_channels, out_channels, kernel_size=3, stride=1, padding=1, bias=False, **kwargs)
        self.scale2 = LearnableScale(out_channels)
        self.nonlinear2 = RPRelu(self.rpmode)
        self.downsample = downsample
        self.stride = stride
        self.out_channels = out_channels

    def forward(self, x):
        identity = x

        out = self.bn1(x)
        out = self.conv1(out)
        out = self.scale1(out)
        out = self.nonlinear1(out)
        if self.downsample is not None:
            identity = self.downsample(x)
        out += identity

        identity = out
        out = self.bn2(out)
        out = self.conv2(out)
        out = self.scale2(out)
        out = self.nonlinear2(out)
        out += identity

        return out

class RANetBlockA(nn.Module):
    expansion = 1

    def __init__(self, in_channels, out_channels, stride=1, downsample=None, Expand_num=1,rpgroup=1,gp=1,**kwargs):
        super(RANetBlockA, self).__init__()
        if rpgroup == 1:
            self.rpmode = out_channels
            self.prelu1 = RPRelu(self.rpmode)
            self.prelu2 = RPRelu(self.rpmode)
            self.move1 = LearnableBias(in_channels)
            self.move2 = LearnableBias(out_channels)
        
        self.conv1 = RAConv2d(in_channels, out_channels, kernel_size=3, stride=stride, padding=1, bias=False, **kwargs)
        self.bn1 = nn.BatchNorm2d(out_channels)
        
        self.conv2 = RAConv2d(out_channels, out_channels, kernel_size=3, stride=1, padding=1, bias=False, **kwargs)
        self.bn2 = nn.BatchNorm2d(out_channels)
        
        self.downsample = downsample
        self.stride = stride
        self.out_channels = out_channels

    def forward(self, x):
        identity = x
        x = self.move1(x)
        out = self.conv1(x)
        out = self.bn1(out)
        if self.downsample is not None:
            identity = self.downsample(x)
        out += identity
        out = self.prelu1(out)

        identity = out
        
        out = self.move2(out)
        out = self.conv2(out)
        out = self.bn2(out)

        out += identity
        out = self.prelu2(out)
        return out

class RANetBlockB(nn.Module):
    def __init__(self, inplanes, planes, stride=1, Expand_num=0.001,rpgroup=1,gp=1,**kwargs):
        super(RANetBlockB, self).__init__()
        
        #norm_layer = nn.BatchNorm2d
        if rpgroup == 1:
            self.prelu1 = RPRelu(inplanes)
            self.prelu2 = RPRelu(planes)
            #self.move1 = LearnableBias(inplanes)
            #self.move2 = LearnableBias(inplanes)
        elif rpgroup == 2:
            if planes == 51200:
                self.prelu1 = GPRPRelu(inplanes,gp=gp)
                self.prelu2 = GPRPRelu(planes,gp=gp)
            elif planes == 1024 :
                if inplanes != planes:
                    # self.prelu1 = RPRelu(inplanes)
                    # self.prelu2 = GPRPRelu(planes,gp=gp)
                    # self.move1 = LearnableBias(inplanes)
                    # self.move2 = GPLearnableBias(inplanes,gp=gp)
                    self.prelu1 = GPRPRelu(inplanes,gp=gp)
                    self.prelu2 = GPRPRelu(planes,gp=gp)
                    #self.move1 = GPLearnableBias(inplanes,gp=gp//2)
                    #self.move2 = GPLearnableBias(inplanes,gp=gp//2)
                else:
                    self.prelu1 = GPRPRelu(inplanes,gp=gp)
                    self.prelu2 = GPRPRelu(planes,gp=gp)
                    #self.move1 = GPLearnableBias(inplanes,gp=gp)
                    #self.move2 = GPLearnableBias(inplanes,gp=gp)
            else:
                self.prelu1 = RPRelu(inplanes)
                self.prelu2 = RPRelu(planes)
                #self.move1 = LearnableBias(inplanes)
                #self.move2 = LearnableBias(inplanes)

        self.rebias1 = nn.Parameter(torch.zeros(1),requires_grad=True)
        self.rebias2 = nn.Parameter(torch.zeros(1),requires_grad=True)
        #self.adbias1 = nn.Parameter(torch.zeros(1,inplanes,1,1),requires_grad=True)
        #self.adbias2 = nn.Parameter(torch.zeros(1,inplanes,1,1),requires_grad=True)
        self.binary_3x3 = RAConv2d(inplanes, inplanes, kernel_size=3, stride=stride, padding=1, bias=False, **kwargs)
        self.bn1 = nn.BatchNorm2d(inplanes)
        #self.expandnum = Expand_num
        #self.st = torch.tensor(Expand_num).float().cuda()

        

        if inplanes == planes:
            
            self.binary_pw = RAConv2d(inplanes, planes, kernel_size=1, stride=1, padding=0, bias=False, **kwargs)
            self.bn2 = nn.BatchNorm2d(planes)
        else:
            #self.bias21 = nn.Parameter(torch.ones(1,inplanes,1,1),requires_grad=True)
            #self.bias22 = nn.Parameter(torch.ones(1,inplanes,1,1),requires_grad=True)
            self.binary_pw_down1 = RAConv2d(inplanes, inplanes, kernel_size=1, stride=1, padding=0, bias=False,
                                            **kwargs)
            self.binary_pw_down2 = RAConv2d(inplanes, inplanes, kernel_size=1, stride=1, padding=0, bias=False,
                                            **kwargs)
            self.bn2_1 = nn.BatchNorm2d(inplanes)
            self.bn2_2 = nn.BatchNorm2d(inplanes)

        self.stride = stride
        self.inplanes = inplanes
        self.planes = planes

        if self.inplanes != self.planes:
            self.pooling = nn.AvgPool2d(2, 2)

    def forward(self, x):

        #out1 = self.sbias1(x)
        #out1 = self.move1(x)

        #out1 = biasaddtry().apply(x,self.adbias1,self.st)
        #out1 = x+self.expandnum
        out1 = x+self.rebias1
        out1 = self.binary_3x3(out1)
        out1 = self.bn1(out1)

        if self.stride == 2:
            x = self.pooling(x)

        out1 = x + out1

        out1 = self.prelu1(out1)
        out2 = out1+self.rebias2
        #out2 = out1+self.expandnum
        #out2 =self.sbias2(out1)
        #out2 = self.move2(out1)
        #out2 = biasaddtry().apply(out1,self.adbias2,self.st)

        if self.inplanes == self.planes:
            out2 = self.binary_pw(out2)
            out2 = self.bn2(out2)
            out2 += out1

        else:
            assert self.planes == self.inplanes * 2

            out2_1 = self.binary_pw_down1(out2)
            out2_2 = self.binary_pw_down2(out2)
            out2_1 = self.bn2_1(out2_1)
            out2_2 = self.bn2_2(out2_2)
            out2_1 += out1
            out2_2 += out1
            out2 = torch.cat([out2_1, out2_2], dim=1)

        out2 = self.prelu2(out2)

        return out2

class RANetBlockFL(nn.Module):
    def __init__(self, inplanes, planes, stride=1, Expand_num=0.001,rpgroup=1,gp=1,**kwargs):
        super(RANetBlockFL, self).__init__()
        
        #norm_layer = nn.BatchNorm2d
        if rpgroup == 1:
            self.prelu1 = RPRelu(inplanes)
            self.prelu2 = RPRelu(planes)

        self.binary_3x3 = RAConv2d(inplanes, inplanes, kernel_size=3, stride=stride, padding=1, bias=False, **kwargs)
        self.bn1 = nn.BatchNorm2d(inplanes)
        #self.expandnum = Expand_num
        #self.st = torch.tensor(Expand_num).float().cuda()

        

        if inplanes == planes:
            
            self.binary_pw = RAConv2d(inplanes, planes, kernel_size=1, stride=1, padding=0, bias=False, **kwargs)
            self.bn2 = nn.BatchNorm2d(planes)
        else:
            #self.bias21 = nn.Parameter(torch.ones(1,inplanes,1,1),requires_grad=True)
            #self.bias22 = nn.Parameter(torch.ones(1,inplanes,1,1),requires_grad=True)
            self.binary_pw_down1 = RAConv2d(inplanes, inplanes, kernel_size=1, stride=1, padding=0, bias=False,
                                            **kwargs)
            self.binary_pw_down2 = RAConv2d(inplanes, inplanes, kernel_size=1, stride=1, padding=0, bias=False,
                                            **kwargs)
            self.bn2_1 = nn.BatchNorm2d(inplanes)
            self.bn2_2 = nn.BatchNorm2d(inplanes)

        self.stride = stride
        self.inplanes = inplanes
        self.planes = planes

        if self.inplanes != self.planes:
            self.pooling = nn.AvgPool2d(2, 2)

    def forward(self, x):

        #out1 = self.sbias1(x)
        #out1 = self.move1(x)

        #out1 = biasaddtry().apply(x,self.adbias1,self.st)
        #out1 = x+self.expandnum
        out1 = x
        out1 = self.binary_3x3(out1)
        out1 = self.bn1(out1)

        if self.stride == 2:
            x = self.pooling(x)

        out1 = x + out1

        out1 = self.prelu1(out1)
        out2 = out1
        #out2 = self.move2(out1)
        #out2 = biasaddtry().apply(out1,self.adbias2,self.st)

        if self.inplanes == self.planes:
            out2 = self.binary_pw(out2)
            out2 = self.bn2(out2)
            out2 += out1

        else:
            assert self.planes == self.inplanes * 2

            out2_1 = self.binary_pw_down1(out2)
            out2_2 = self.binary_pw_down2(out2)
            out2_1 = self.bn2_1(out2_1)
            out2_2 = self.bn2_2(out2_2)
            out2_1 += out1
            out2_2 += out1
            out2 = torch.cat([out2_1, out2_2], dim=1)

        out2 = self.prelu2(out2)

        return out2
class RANetBlockC(nn.Module):
    def __init__(self, inplanes, planes, stride=1, Expand_num=1,rpgroup=1,gp=1,**kwargs):
        super(RANetBlockC, self).__init__()
        #norm_layer = nn.BatchNorm2d
        if rpgroup == 1:
            self.prelu1 = RPRelu(inplanes)
            self.prelu2 = RPRelu(planes)
            #self.move1 = LearnableBias(inplanes)
            #self.move2 = LearnableBias(inplanes)

        
        self.binary_3x3 = RAConv2d(inplanes, inplanes, kernel_size=3, stride=stride, padding=1, bias=False, **kwargs)
        self.bn1 = nn.BatchNorm2d(inplanes)
        self.expandnum = Expand_num

        self.scalebias1 = scalebias(inplanes)


        

        if inplanes == planes:
            self.binary_pw = RAConv2d(inplanes, planes, kernel_size=1, stride=1, padding=0, bias=False, **kwargs)
            self.bn2 = nn.BatchNorm2d(planes)
            self.scalebias2 = scalebias(inplanes)
        else:
            self.binary_pw_down1 = RAConv2d(inplanes, inplanes, kernel_size=1, stride=1, padding=0, bias=False,
                                            **kwargs)
            self.binary_pw_down2 = RAConv2d(inplanes, inplanes, kernel_size=1, stride=1, padding=0, bias=False,
                                            **kwargs)
            self.bn2_1 = nn.BatchNorm2d(inplanes)
            self.bn2_2 = nn.BatchNorm2d(inplanes)
            self.scalebias21 = scalebias(inplanes)
            self.scalebias22 = scalebias(inplanes)

        self.stride = stride
        self.inplanes = inplanes
        self.planes = planes

        if self.inplanes != self.planes:
            self.pooling = nn.AvgPool2d(2, 2)

    def forward(self, x):

        #out1 = self.move1(x)

        out1 = x-self.expandnum
        out1 = self.binary_3x3(out1)
        out1 = self.bn1(out1)

        if self.stride == 2:
            x = self.pooling(x)

        x = self.scalebias1(x)
        out1 = x + out1

        out1 = self.prelu1(out1)

        #out2 = self.move2(out1)
        out2 = out1-self.expandnum

        if self.inplanes == self.planes:
            out2 = self.binary_pw(out2)
            out2 = self.bn2(out2)
            out1 = self.scalebias2(out1)
            out2 += out1

        else:
            assert self.planes == self.inplanes * 2

            out2_1 = self.binary_pw_down1(out2)
            out2_2 = self.binary_pw_down2(out2)
            out2_1 = self.bn2_1(out2_1)
            out2_2 = self.bn2_2(out2_2)
            out11 = self.scalebias21(out1)
            out12 = self.scalebias22(out1)
            out2_1 += out11
            out2_2 += out12
            out2 = torch.cat([out2_1, out2_2], dim=1)

        out2 = self.prelu2(out2)

        return out2

class RANetBlockD(nn.Module): ##rsign??????????????????shortcut????????????
    def __init__(self, inplanes, planes, stride=1, Expand_num=1,rpgroup=1,gp=1,**kwargs):
        super(RANetBlockD, self).__init__()
        #norm_layer = nn.BatchNorm2d
        if rpgroup == 1:
            self.prelu1 = RPRelu(inplanes)
            self.prelu2 = RPRelu(planes)
            # if Expand_num==1:
            #     chn = 1
            # elif Expand_num==2:
            #     chn = inplanes
            self.move1 = nn.Parameter(torch.zeros(1,inplanes,1,1), requires_grad=True)
            self.move2 = nn.Parameter(torch.zeros(1,inplanes,1,1), requires_grad=True)
        elif rpgroup == 2:
            if planes == 51200:
                self.prelu1 = GPRPRelu(inplanes,gp=gp)
                self.prelu2 = GPRPRelu(planes,gp=gp)
            elif planes == 1024 :
                if inplanes != planes:
                    # self.prelu1 = RPRelu(inplanes)
                    # self.prelu2 = GPRPRelu(planes,gp=gp)
                    # self.move1 = LearnableBias(inplanes)
                    # self.move2 = GPLearnableBias(inplanes,gp=gp)
                    self.prelu1 = GPRPRelu(inplanes,gp=gp)
                    self.prelu2 = GPRPRelu(planes,gp=gp)
                    #self.move1 = GPLearnableBias(inplanes,gp=gp//2)
                    #self.move2 = GPLearnableBias(inplanes,gp=gp//2)
                else:
                    self.prelu1 = GPRPRelu(inplanes,gp=gp)
                    self.prelu2 = GPRPRelu(planes,gp=gp)
                    #self.move1 = GPLearnableBias(inplanes,gp=gp)
                    #self.move2 = GPLearnableBias(inplanes,gp=gp)
            else:
                self.prelu1 = RPRelu(inplanes)
                self.prelu2 = RPRelu(planes)
                #self.move1 = LearnableBias(inplanes)
                #self.move2 = LearnableBias(inplanes)

        
        self.binary_3x3 = RAConv2d(inplanes, inplanes, kernel_size=3, stride=stride, padding=1, bias=False, **kwargs)
        self.bn1 = nn.BatchNorm2d(inplanes)
        self.expandnum = Expand_num


        

        if inplanes == planes:
            self.binary_pw = RAConv2d(inplanes, planes, kernel_size=1, stride=1, padding=0, bias=False, **kwargs)
            self.bn2 = nn.BatchNorm2d(planes)
        else:
            self.binary_pw_down1 = RAConv2d(inplanes, inplanes, kernel_size=1, stride=1, padding=0, bias=False,
                                            **kwargs)
            self.binary_pw_down2 = RAConv2d(inplanes, inplanes, kernel_size=1, stride=1, padding=0, bias=False,
                                            **kwargs)
            self.bn2_1 = nn.BatchNorm2d(inplanes)
            self.bn2_2 = nn.BatchNorm2d(inplanes)

        self.stride = stride
        self.inplanes = inplanes
        self.planes = planes

        if self.inplanes != self.planes:
            self.pooling = nn.AvgPool2d(2, 2)

    def forward(self, x):

        x = x+self.move1.expand_as(x)
        out1 = x
        #out1 = x-self.expandnum
        out1 = out1-self.expandnum
        out1 = self.binary_3x3(out1)
        out1 = self.bn1(out1)

        if self.stride == 2:
            x = x-self.move1.expand_as(x).detach()
            x = self.pooling(x)
            out1 = x + out1
        else:
            x = x-self.move1.expand_as(x).detach()
            out1 = x + out1


        

        out1 = self.prelu1(out1)
        out1 = out1 +self.move2.expand_as(out1)
        out2 = out1
        out2 = out2-self.expandnum

        if self.inplanes == self.planes:
            out2 = self.binary_pw(out2)
            out2 = self.bn2(out2)
            out2 =out2+out1-self.move2.expand_as(out1).detach()

        else:
            assert self.planes == self.inplanes * 2

            out2_1 = self.binary_pw_down1(out2)
            out2_2 = self.binary_pw_down2(out2)
            out2_1 = self.bn2_1(out2_1)
            out2_2 = self.bn2_2(out2_2)
            out2_1 = out2_1+out1-self.move2.expand_as(out1).detach()
            out2_2 = out2_2+out1-self.move2.expand_as(out1).detach()
            out2 = torch.cat([out2_1, out2_2], dim=1)

        out2 = self.prelu2(out2)

        return out2

class RANetBlockE(nn.Module):
    def __init__(self, inplanes, planes, stride=1, Expand_num=1,rpgroup=1,gp=1,**kwargs):
        super(RANetBlockE, self).__init__()
        #norm_layer = nn.BatchNorm2d
        if rpgroup == 1:
            self.prelu1 = RPRelu(inplanes)
            self.prelu2 = RPRelu(planes)
            #self.move1 = LearnableBias(inplanes)
            #self.move2 = LearnableBias(inplanes)
        elif rpgroup == 2:
            if planes == 51200:
                self.prelu1 = GPRPRelu(inplanes,gp=gp)
                self.prelu2 = GPRPRelu(planes,gp=gp)
            elif planes == 1024 :
                if inplanes != planes:
                    # self.prelu1 = RPRelu(inplanes)
                    # self.prelu2 = GPRPRelu(planes,gp=gp)
                    # self.move1 = LearnableBias(inplanes)
                    # self.move2 = GPLearnableBias(inplanes,gp=gp)
                    self.prelu1 = GPRPRelu(inplanes,gp=gp)
                    self.prelu2 = GPRPRelu(planes,gp=gp)
                    #self.move1 = GPLearnableBias(inplanes,gp=gp//2)
                    #self.move2 = GPLearnableBias(inplanes,gp=gp//2)
                else:
                    self.prelu1 = GPRPRelu(inplanes,gp=gp)
                    self.prelu2 = GPRPRelu(planes,gp=gp)
                    #self.move1 = GPLearnableBias(inplanes,gp=gp)
                    #self.move2 = GPLearnableBias(inplanes,gp=gp)
            else:
                self.prelu1 = RPRelu(inplanes)
                self.prelu2 = RPRelu(planes)
                #self.move1 = LearnableBias(inplanes)
                #self.move2 = LearnableBias(inplanes)

        
        self.binary_3x3 = RAConv2d(inplanes, inplanes, kernel_size=3, stride=stride, padding=1, bias=False, **kwargs)
        self.bn1 = nn.BatchNorm2d(inplanes)
        #self.expandnum = Expand_num
        self.rebias1 = nn.Parameter(torch.zeros(1),requires_grad=True)
        self.rebias2 = nn.Parameter(torch.zeros(1),requires_grad=True)
        self.scalebias1 = scalebias(inplanes)


        

        if inplanes == planes:
            self.binary_pw = RAConv2d(inplanes, planes, kernel_size=1, stride=1, padding=0, bias=False, **kwargs)
            self.bn2 = nn.BatchNorm2d(planes)
            self.scalebias2 = scalebias(inplanes)
        else:
            self.binary_pw_down1 = RAConv2d(inplanes, inplanes, kernel_size=1, stride=1, padding=0, bias=False,
                                            **kwargs)
            self.binary_pw_down2 = RAConv2d(inplanes, inplanes, kernel_size=1, stride=1, padding=0, bias=False,
                                            **kwargs)
            self.bn2_1 = nn.BatchNorm2d(inplanes)
            self.bn2_2 = nn.BatchNorm2d(inplanes)
            self.scalebias21 = scalebias(inplanes)
            self.scalebias22 = scalebias(inplanes)

        self.stride = stride
        self.inplanes = inplanes
        self.planes = planes

        if self.inplanes != self.planes:
            self.pooling = nn.AvgPool2d(2, 2)

    def forward(self, x):

        #out1 = self.move1(x)

        out1 = x+self.rebias1
        out1 = self.binary_3x3(out1)
        out1 = self.bn1(out1)

        if self.stride == 2:
            x = self.pooling(x)

        x = self.scalebias1(x)
        out1 = x + out1

        out1 = self.prelu1(out1)

        #out2 = self.move2(out1)
        out2 = out1+self.rebias2

        if self.inplanes == self.planes:
            out2 = self.binary_pw(out2)
            out2 = self.bn2(out2)
            out1 = self.scalebias2(out1)
            out2 += out1

        else:
            assert self.planes == self.inplanes * 2

            out2_1 = self.binary_pw_down1(out2)
            out2_2 = self.binary_pw_down2(out2)
            out2_1 = self.bn2_1(out2_1)
            out2_2 = self.bn2_2(out2_2)
            out11 = self.scalebias21(out1)
            out12 = self.scalebias22(out1)
            out2_1 += out11
            out2_2 += out12
            out2 = torch.cat([out2_1, out2_2], dim=1)

        out2 = self.prelu2(out2)

        return out2
class Baseline15Block(nn.Module):
    expansion = 1

    def __init__(self, in_channels, out_channels, stride=1, downsample=None,Expand_num=1,rpgroup=1,gp=1, **kwargs):
        super(Baseline15Block, self).__init__()
        if rpgroup == 1:
            self.rpmode = 1
        elif rpgroup == 2:
            self.rpmode = out_channels
        self.conv1 = RAConv2d(in_channels, out_channels, kernel_size=3, stride=stride, padding=1, bias=False, **kwargs)
        self.bn11 = nn.BatchNorm2d(out_channels)
        self.nonlinear1 = RPRelu(self.rpmode)
        self.bn12 = nn.BatchNorm2d(out_channels)
        self.conv2 = RAConv2d(out_channels, out_channels, kernel_size=3, stride=1, padding=1, bias=False, **kwargs)
        self.bn21 = nn.BatchNorm2d(out_channels)
        self.nonlinear2 = RPRelu(self.rpmode)
        self.bn22 = nn.BatchNorm2d(out_channels)
        self.downsample = downsample
        self.stride = stride
        self.out_channels = out_channels

    def forward(self, x):
        identity = x

        out = self.conv1(x)
        out = self.bn11(out)
        out = self.nonlinear1(out)
        if self.downsample is not None:
            identity = self.downsample(x)
        out += identity
        out = self.bn12(out)

        identity = out
        out = self.conv2(out)
        out = self.bn21(out)
        out = self.nonlinear2(out)
        out += identity
        out = self.bn22(out)

        return out


class Baseline13_Block(nn.Module):
    expansion = 1

    def __init__(self, in_channels, out_channels, stride=1, downsample=None, Expand_num=1,  rpgroup=1,gp=1,**kwargs):
        super(Baseline13_Block, self).__init__()
        self.out_channels = out_channels
        self.stride = stride
        self.downsample = downsample
        self.Expand_num = Expand_num
        self.fexpand1 = Expandx(Expand_num=Expand_num, in_channels=in_channels)
        self.conv1 = RAConv2d(in_channels * Expand_num, out_channels, kernel_size=3, stride=stride, padding=1, bias=False, **kwargs)
        #self.nonlinear11 = LearnableScale(out_channels)
        self.bn1 = nn.BatchNorm2d(out_channels)
        #self.nonlinear12 = RPRelu(self.rpmode)
        self.nonlinear11 = nn.PReLU(out_channels) 
        self.fexpand2 = Expandx(Expand_num=Expand_num, in_channels=out_channels)
        self.conv2 = RAConv2d(out_channels * Expand_num, out_channels, kernel_size=3, stride=1, padding=1, bias=False, **kwargs)
        #self.nonlinear21 = LearnableScale(out_channels)
        self.bn2 = nn.BatchNorm2d(out_channels)
        #self.nonlinear22 = RPRelu(self.rpmode)


    def forward(self, x):
        identity = x

        out = self.fexpand1(x)
        out = self.conv1(out)   
        out = self.nonlinear11(out)
        #out = self.nonlinear12(out)
        out = self.bn1(out)
        if self.downsample is not None:
            identity = self.downsample(x)
        out += identity
        

        identity = out
        out = self.fexpand2(out)
        out = self.conv2(out)
        #out = self.nonlinear21(out)
        #out = self.nonlinear22(out)
        out = self.bn2(out)
        out += identity


        return out
class RANetBlockDE(nn.Module):
    def __init__(self, inplanes, planes, stride=1, Expand_num=1,rpgroup=1,gp=1,**kwargs):
        super(RANetBlockDE, self).__init__()
        #norm_layer = nn.BatchNorm2d
        if rpgroup == 1:
            self.prelu1 = RPRelu(inplanes)
            self.prelu2 = RPRelu(planes)
            #self.move1 = LearnableBias(inplanes)
            #self.move2 = LearnableBias(inplanes)
        
        self.binary_3x3 = RAConv2d(inplanes, inplanes, kernel_size=3, stride=stride, padding=1, bias=False, **kwargs)
        self.bn1 = nn.BatchNorm2d(inplanes)

        

        if inplanes == planes:
            self.binary_pw = RAConv2d(inplanes, planes, kernel_size=1, stride=1, padding=0, bias=False, **kwargs)
            self.bn2 = nn.BatchNorm2d(planes)
        else:
            self.binary_pw_down1 = RAConv2d(inplanes, inplanes, kernel_size=1, stride=1, padding=0, bias=False,
                                            **kwargs)
            self.binary_pw_down2 = RAConv2d(inplanes, inplanes, kernel_size=1, stride=1, padding=0, bias=False,
                                            **kwargs)
            self.bn2_1 = nn.BatchNorm2d(inplanes)
            self.bn2_2 = nn.BatchNorm2d(inplanes)

        self.stride = stride
        self.inplanes = inplanes
        self.planes = planes

        if self.inplanes != self.planes:
            self.pooling = nn.AvgPool2d(2, 2)

    def forward(self, x):

        #out1 = self.move1(x)

        out1 = x
        out1 = self.binary_3x3(out1)
        out1 = self.bn1(out1)

        if self.stride == 2:
            x = self.pooling(x)

        out1 = x + out1

        out1 = self.prelu1(out1)

        #out2 = self.move2(out1)
        out2 = out1

        if self.inplanes == self.planes:
            out2 = self.binary_pw(out2)
            out2 = self.bn2(out2)
            out2 += out1

        else:
            assert self.planes == self.inplanes * 2

            out2_1 = self.binary_pw_down1(out2)
            out2_2 = self.binary_pw_down2(out2)
            out2_1 = self.bn2_1(out2_1)
            out2_2 = self.bn2_2(out2_2)
            out2_1 += out1
            out2_2 += out2
            out2 = torch.cat([out2_1, out2_2], dim=1)

        out2 = self.prelu2(out2)

        return out2