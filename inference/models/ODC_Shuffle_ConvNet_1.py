import torch.nn as nn
import torch.nn.functional as F
import torch
from inference.models.RJ_grasp_model import GraspModel, OSAModule, OSABlock, TransitionBlock
from inference.models.cbam import CBAM

class Generative_ODC_Shuffle_1(GraspModel):

    def __init__(self, input_channels=4, output_channels=1, channel_size=256, dropout=False, prob=0.0):
        super(Generative_ODC_Shuffle_1, self).__init__()

        print("Generative_ODC_Shuffle_1")

        self.conv1 = nn.Conv2d(input_channels, channel_size, kernel_size=9, stride=1, padding=4)
        self.bn1 = nn.BatchNorm2d(channel_size)

        self.conv2 = nn.Conv2d(channel_size, channel_size * 2, kernel_size=4, stride=2, padding=1)
        self.bn2 = nn.BatchNorm2d(channel_size * 2)

        self.conv3 = nn.Conv2d(channel_size * 2, channel_size * 4, kernel_size=4, stride=2, padding=1)
        self.bn3 = nn.BatchNorm2d(channel_size * 4)

        self.conv_out_size = channel_size * 4

        self.shuffle_factor = [2, 2]
        
        self.osa_depth = 5
        self.osa_conv_kernal = [64, 40, 48, 56]
        self.trans_conv_kernal = [128, 128, 192, 256]
        self.osa_drop_rate = 0.0
        self.osa_reduction = 1.0

         # 1st block
        self.block1 = OSABlock(self.osa_depth, self.conv_out_size, self.osa_conv_kernal[0], OSAModule, self.osa_drop_rate)
        self.trans1 = TransitionBlock(self.osa_conv_kernal[0]*self.osa_depth, self.trans_conv_kernal[0], dropRate=self.osa_drop_rate)
        self.cbam1 = CBAM(self.trans_conv_kernal[0])

        # 2nd block
        self.block2 = OSABlock(self.osa_depth, self.trans_conv_kernal[0], self.osa_conv_kernal[1], OSAModule, self.osa_drop_rate)
        self.trans2 = TransitionBlock(self.osa_conv_kernal[1]*self.osa_depth, self.trans_conv_kernal[1], dropRate=self.osa_drop_rate)
        self.cbam2 = CBAM(self.trans_conv_kernal[1])

        # 3rd block
        self.block3 = OSABlock(self.osa_depth, self.trans_conv_kernal[1], self.osa_conv_kernal[2], OSAModule, self.osa_drop_rate)
        self.trans3 = TransitionBlock(self.osa_conv_kernal[2]*self.osa_depth, self.trans_conv_kernal[2], dropRate=self.osa_drop_rate)
        self.cbam3 = CBAM(self.trans_conv_kernal[2])

        # 4rd block
        self.block4 = OSABlock(self.osa_depth, self.trans_conv_kernal[2], self.osa_conv_kernal[3], OSAModule, self.osa_drop_rate)
        self.trans4 = TransitionBlock(self.osa_conv_kernal[3]*self.osa_depth, self.trans_conv_kernal[3], dropRate=self.osa_drop_rate)
        self.cbam4 = CBAM(self.trans_conv_kernal[3])

        # self.conv4 = nn.ConvTranspose2d(self.trans_conv_kernal[3], channel_size * 2, kernel_size=4, stride=2, padding=1,
        #                                 output_padding=1)
        # self.bn4 = nn.BatchNorm2d(channel_size * 2)

        # self.conv5 = nn.ConvTranspose2d(channel_size * 2, channel_size, kernel_size=4, stride=2, padding=2,
        #                                 output_padding=1)
        # self.bn5 = nn.BatchNorm2d(channel_size)


        self.conv4 = nn.Conv2d(self.trans_conv_kernal[3], channel_size*4, kernel_size=3, stride=1, padding=1)
        self.sf1 = nn.PixelShuffle(self.shuffle_factor[1])
        self.bn4 = nn.BatchNorm2d(32)

        self.conv5 = nn.Conv2d(32, channel_size*2, kernel_size=3, stride=1, padding=1)
        self.sf2 = nn.PixelShuffle(self.shuffle_factor[0])
        self.bn5 = nn.BatchNorm2d(16)

        self.conv6 = nn.Conv2d(16, channel_size, kernel_size=3, stride=1, padding=1)
        self.bn6 = nn.BatchNorm2d(channel_size)


        self.pos_output = nn.Conv2d(in_channels=channel_size, out_channels=output_channels, kernel_size=3, padding=1)
        self.cos_output = nn.Conv2d(in_channels=channel_size, out_channels=output_channels, kernel_size=3, padding=1)
        self.sin_output = nn.Conv2d(in_channels=channel_size, out_channels=output_channels, kernel_size=3, padding=1)
        self.width_output = nn.Conv2d(in_channels=channel_size, out_channels=output_channels, kernel_size=3, padding=1)

        self.dropout = dropout
        self.dropout_pos = nn.Dropout(p=prob)
        self.dropout_cos = nn.Dropout(p=prob)
        self.dropout_sin = nn.Dropout(p=prob)
        self.dropout_wid = nn.Dropout(p=prob)

        for m in self.modules():
            if isinstance(m, (nn.Conv2d, nn.ConvTranspose2d)):
                nn.init.xavier_uniform_(m.weight, gain=1)


    def forward(self, x_in):

        x = F.relu(self.bn1(self.conv1(x_in)))
        x = F.relu(self.bn2(self.conv2(x)))
        x = F.relu(self.bn3(self.conv3(x)))

        x = self.trans1(self.block1(x))
        x = self.cbam1(x)
        x = self.trans2(self.block2(x))
        x = self.cbam2(x)
        x = self.trans3(self.block3(x))
        x = self.cbam3(x)
        x = self.trans4(self.block4(x))
        x = self.cbam4(x)

        x = F.relu(self.bn4(self.sf1(self.conv4(x))))
        x = F.relu(self.bn5(self.sf2(self.conv5(x))))
        x = F.relu(self.bn6((self.conv6(x))))


        if self.dropout:
            pos_output = self.pos_output(self.dropout_pos(x))
            cos_output = self.cos_output(self.dropout_cos(x))
            sin_output = self.sin_output(self.dropout_sin(x))
            width_output = self.width_output(self.dropout_wid(x))
        else:
            pos_output = self.pos_output(x)
            cos_output = self.cos_output(x)
            sin_output = self.sin_output(x)
            width_output = self.width_output(x)

        return pos_output, cos_output, sin_output, width_output