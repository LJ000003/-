#include "STC15F2K60S2.H"        //必须。
#include "sys.H"                 //必须。
#include "displayer.H" 
#include "key.h"
#include "Ir.h"
#include "beep.h"
#include "adc.h"
#define myID 0x02
code unsigned long SysClock=11059200;         //必须。定义系统工作时钟频率(Hz)，用户必须修改成与实际工作频率（下载时选择的）一致
#ifdef _displayer_H_                          //显示模块选用时必须。（数码管显示译码表，用戶可修改、增加等） 
code char decode_table[]={0x00,0x06,0x5b,0x4f,0x66,0x6d,0x7d,0x07,0x7f,0x6f,0x3f,0x1E,0x6B,0x75, 0x40, 0x48,0x76, 
	              /* 序号:   0   1    2	   3    4	    5    6	  7   8	   9	 10	   11		12   13    14     15     */
                /* 显示:   wu  1    2    3    4     5    6    7   8    9    0     J    Q    K     zhong_  中下-   */  
	                       0x3f|0x80,0x06|0x80,0x5b|0x80,0x4f|0x80,0x66|0x80,0x6d|0x80,0x7d|0x80,0x07|0x80,0x7f|0x80,0x6f|0x80 };  
             /* 带小数点     0         1         2         3         4         5         6         7         8         9        */

#endif
unsigned char rxd0[4]={myID,0x00,0x00,0x00};  
unsigned char a=0x00;
unsigned char rxd[4];      
unsigned char send[4]={myID,0x00,0x00,0x00};
unsigned char send1[4]={myID,0x00,0x00,0x00};
unsigned char send2[4]={myID,0x00,0x00,0x00};
void myIrRxd_callback()				      //接收发过来的匹扑克
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

void myAdc_callback()				  //选择要发出去的牌    
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
	SetEventCallBack(enumEventIrRxd, myIrRxd_callback);  //红外
	SetEventCallBack(enumEventKey, myKey_callback);   //按键 
	SetEventCallBack(enumEventNav, myAdc_callback);    //导航
	//SetEventCallBack(enumEventKey, myKey_callback);
  MySTC_Init();	    
	while(1)             	
		{ MySTC_OS();    
		}	             
}                 