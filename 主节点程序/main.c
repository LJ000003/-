#include "STC15F2K60S2.h"
#include "sys.h"
#include "beep.h"
#include "displayer.h"
#include "IR.h"
#include "Key.h"
#include "uart1.h"

code unsigned long SysClock=11059200;         //���롣����ϵͳ����ʱ��Ƶ��(Hz)���û������޸ĳ���ʵ�ʹ���Ƶ�ʣ�����ʱѡ��ģ�һ��
#ifdef _displayer_H_                          //��ʾģ��ѡ��ʱ���롣���������ʾ������Ñ����޸ġ����ӵȣ� 
code char decode_table[]={		0x00,	0x06,0x5b,0x4f,0x66,0x6d,0x7d,0x07,	0x7f,0x6f,0x3f,	0x1E,0x6B,0x75,  
                  /* ���:   	0   	1    2    3    4    5    6    7 		8    9    10    11   12   13       */
                  /* ��ʾ:   	wu  	1    2    3    4    5    6    7   	8    9    0     J    Q    K        */  
                           0x3f|0x80,0x06|0x80,0x5b|0x80,0x4f|0x80,0x66|0x80,0x6d|0x80,0x7d|0x80,0x07|0x80,0x7f|0x80,0x6f|0x80 };  
             /* ��С����     0         1         2         3         4         5         6         7         8         9        */

#endif

unsigned char card[52] = {
    0x07, 0x02, 0x0c, 0x09, 0x0a, 0x0d, 0x03, 0x05, 0x08, 0x01, 0x06, 0x0b, 0x04,
    0x0d, 0x09, 0x02, 0x0a, 0x07, 0x0c, 0x01, 0x0b, 0x03, 0x08, 0x04, 0x06, 0x05,
    0x0b, 0x01, 0x0d, 0x08, 0x04, 0x0c, 0x0a, 0x07, 0x03, 0x09, 0x06, 0x02, 0x05,
    0x06, 0x0c, 0x04, 0x0a, 0x0d, 0x01, 0x08, 0x09, 0x0b, 0x03, 0x07, 0x02, 0x05
};

unsigned char txdbuf[4];//������λ��:���+��
unsigned char txdPC[5];//PC���������+��+�����Ƿ����
unsigned char rxdbuf[4]={0x01,0x01,0x01,0x01};//������λ��:���+��
unsigned char rxdbuf1[4];//���ڴ洢�ϴν��յ�����Ϣ
int card_number=0;//�������

void send_card()//����
{
	int i=1;
	char Key1 = GetKeyAct(enumKey1);
	char Key2 = GetKeyAct(enumKey2);
	char Key3 = GetKeyAct(enumKey3);
	
  if (Key1 == enumKeyPress) 
	{
		txdbuf[0]=0x01;
		for(;i<4;i++)
		{//�ж��ϴθ�λ���Ƿ�δ����
			if(rxdbuf[i]!=0x00)//������
			{
				if(card_number<52)
				{
					txdbuf[i]=card[card_number];
					card_number=card_number+1;
				}
				else //û���ƣ���������
				{
					txdPC[0]=0x01;
					txdPC[1]=0x01;txdPC[2]=0x01;txdPC[3]=0x01;
					txdPC[4]=0x01;
					Uart1Print(txdPC,sizeof(txdPC));
				}
			}
			else//δ����
			{
				txdbuf[i]=0x00;
			}
		}
		IrPrint(txdbuf,sizeof(txdbuf));
		SetBeep(5600,30);
	}
	
	if (Key2 == enumKeyPress) 
	{
		txdbuf[0]=0x02;
		for(;i<4;i++)
		{
			if(rxdbuf[i]!=0x00)
			{
				if(card_number<52)
				{
					txdbuf[i]=card[card_number];
					card_number++;
				}
				else //û���ƣ���������
				{
					txdPC[0]=0x00;
					txdPC[1]=0x0a;txdPC[2]=0x0b;txdPC[3]=0x0c;
					txdPC[4]=0x01;
					Uart1Print(txdPC,sizeof(txdPC));
				}
			}
			else
			{
				txdbuf[i]=0x00;
			}
		}
		IrPrint(txdbuf,sizeof(txdbuf));
		SetBeep(5600,30);
	}

	if (Key3 == enumKeyPress) 
	{//�ٴη����ϴ���ͬ����Ϣ�������ų�������Ϣ
		IrPrint(txdbuf,sizeof(txdbuf));
		SetBeep(5600,30);
	}

}

void send_PC()//���ճ��ƣ���λ��ͨ��
{
	int i=0;
	if(rxdbuf1[0]==rxdbuf[0]&&rxdbuf1[1]==rxdbuf[1]&&rxdbuf1[2]==rxdbuf[2]&&rxdbuf1[3]==rxdbuf[3])
	{	
		SetBeep(7200,100);
		txdPC[0]=rxdbuf[0];
		txdPC[1]=rxdbuf[1];
		txdPC[2]=rxdbuf[2];
		txdPC[3]=rxdbuf[3];
		txdPC[4]=0x00;
		Uart1Print(txdPC,sizeof(txdPC));

	}
	for(;i<4;i++)
	{
		rxdbuf1[i]=rxdbuf[i];
	}
}

void main() 
{ 
	IrInit(NEC_R05d);
	DisplayerInit();
	KeyInit();
	BeepInit();
	Uart1Init(2400);
	
	SetDisplayerArea(0,7);
  Seg7Print(2,0,0,0,0,0,0,0);
	LedPrint(0xff);
	
	SetIrRxd(rxdbuf,sizeof(rxdbuf));
	SetEventCallBack(enumEventKey,send_card);
	SetEventCallBack(enumEventIrRxd,send_PC);
	
	MySTC_Init();	
	while(1)             	
		{ MySTC_OS();    
		}	             
}   