#include "STC15F2K60S2.H"        //���롣
#include "sys.H"                 //���롣
#include "displayer.H" 
#include "key.h"
#include "Ir.h"
#include "beep.h"
#include "adc.h"
#define myID 0x02
code unsigned long SysClock=11059200;         //���롣����ϵͳ����ʱ��Ƶ��(Hz)���û������޸ĳ���ʵ�ʹ���Ƶ�ʣ�����ʱѡ��ģ�һ��
#ifdef _displayer_H_                          //��ʾģ��ѡ��ʱ���롣���������ʾ������Ñ����޸ġ����ӵȣ� 
code char decode_table[]={0x00,0x06,0x5b,0x4f,0x66,0x6d,0x7d,0x07,0x7f,0x6f,0x3f,0x1E,0x6B,0x75, 0x40, 0x48,0x76, 
	              /* ���:   0   1    2	   3    4	    5    6	  7   8	   9	 10	   11		12   13    14     15     */
                /* ��ʾ:   wu  1    2    3    4     5    6    7   8    9    0     J    Q    K     zhong_  ����-   */  
	                       0x3f|0x80,0x06|0x80,0x5b|0x80,0x4f|0x80,0x66|0x80,0x6d|0x80,0x7d|0x80,0x07|0x80,0x7f|0x80,0x6f|0x80 };  
             /* ��С����     0         1         2         3         4         5         6         7         8         9        */

#endif
unsigned char rxd0[4]={myID,0x00,0x00,0x00};  
unsigned char a=0x00;
unsigned char rxd[4];      
unsigned char send[4]={myID,0x00,0x00,0x00};
unsigned char send1[4]={myID,0x00,0x00,0x00};
unsigned char send2[4]={myID,0x00,0x00,0x00};
void myIrRxd_callback()				      //���շ�������ƥ�˿�
{ 
	int flag=0;
	int i=1;
	if(GetIrRxNum() !=0)
	{	 if((rxd[0] == myID ) )
		  {	
				if(rxd[1]==rxd0[1]&&rxd[2]==rxd0[2]&&rxd[3]==rxd0[3])
						flag=1;
				if(flag==1){
					for( i=1;i<4;i++)
					{
						if(rxd[i]!=0x00)
							send2[i]=rxd[i];
					}
					Seg7Print(send2[1],0,0,send2[2],0,0,0,send2[3]);
				}
				for( i=0;i<4;i++)
				{
						rxd0[i]=rxd[i];
				}
				
				
				
				
				
				
				/*
				for( ;i<4;i++)
				{
						if(rxd[i]!=0x00)
							send2[i]=rxd[i];
				}
				Seg7Print(send2[1],0,0,send2[2],0,0,0,send2[3]);*/
			}
  }
}

void myAdc_callback()				  //ѡ��Ҫ����ȥ����    
{ 
	char Left=GetAdcNavAct(enumAdcNavKeyLeft);
	char Center = GetAdcNavAct(enumAdcNavKeyCenter);
	char Right = GetAdcNavAct(enumAdcNavKeyRight);
	if (Left == enumKeyPress) 
	{
		send[1]=send2[1];
		send2[1]=0x00;
		SetBeep(4000,10);
		a+=0x80;
		LedPrint(a);
	}
	
	if (Center == enumKeyPress) 
	{
		send[2]=send2[2];
		send2[2]=0x00;
		SetBeep(4000,10);
		a+=0x10;
		LedPrint(a);
	}
	
	if (Right == enumKeyPress) 
	{
		send[3]=send2[3];
		send2[3]=0x00;
		SetBeep(4000,10);
		a+=0x01;
		LedPrint(a);
	}
}


void myKey_callback()
{
	char Key1 = GetKeyAct(enumKey1);
	char Key2 = GetKeyAct(enumKey2);
	if (Key1 == enumKeyPress) 
	{
		SetBeep(4000,10);
		IrPrint(send,sizeof(send));
		send1[0]=send[0];
		send1[1]=send[1];
		send1[2]=send[2];
		send1[3]=send[3];
		Seg7Print(send2[1],0,0,send2[2],0,0,0,send2[3]);
		send[1]=0x00;
		send[2]=0x00;
		send[3]=0x00;
		
	}
	if (Key2 == enumKeyPress) 
	{
		a=0x00;
		LedPrint(a);
		SetBeep(4000,10);
		IrPrint(send1,sizeof(send1));
		//Seg7Print(rxd[1],0,0,rxd[2],0,0,0,rxd[3]);
	}
}


void main() 
{ 
	KeyInit();
	BeepInit();
	DisplayerInit(); 
  AdcInit(ADCexpEXT);	
	IrInit(NEC_R05d);
	LedPrint(0);
	SetBeep(4000,50);
	SetDisplayerArea(0,7);
	Seg7Print(14,14,14,myID,14,14,14,14);
 
	SetIrRxd(rxd,sizeof(rxd)); 
	SetEventCallBack(enumEventIrRxd, myIrRxd_callback);  //����
	SetEventCallBack(enumEventKey, myKey_callback);   //���� 
	SetEventCallBack(enumEventNav, myAdc_callback);    //����
	//SetEventCallBack(enumEventKey, myKey_callback);
  MySTC_Init();	    
	while(1)             	
		{ MySTC_OS();    
		}	             
}                 