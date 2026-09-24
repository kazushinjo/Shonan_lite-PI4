#include <unistd.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <fcntl.h>
#include <math.h>
#include <linux/fb.h>
#include <sys/mman.h>
#include <sys/ioctl.h>
#include <stdint.h>

#include "Font.h"

// ★Shonan_lite-PI4統合版パッチ: ボタン(displayButton系)と大きな周波数表示を
// FreeType+TTF(Liberation Sans Bold)でアンチエイリアス描画するための状態。
// ttFontReady==0の間は従来のドットフォント/直角ボタン枠にフォールバックする
// (フォントファイルが実機に無い等の場合でもアプリを壊さないため)。
#include <ft2build.h>
#include FT_FREETYPE_H

FT_Library ttLibrary;
FT_Face ttFace;
int ttFontReady = 0;
// ★Shonan_lite-PI4統合版パッチ: ボタン文字は太字だと圧迫感があるとのことで、
// 周波数表示(ttFace、Bold)とは別にレギュラーウェイトのフェイスを用意した。
FT_Face ttFaceButton;
int ttFontButtonReady = 0;

void initTTFont(void);
static int measureTextTTFFace(FT_Face face, const char *s);
static void drawTextTTFFace(FT_Face face, const char *s, int x, int baselineY, int R, int G, int B);
static void drawRoundedButtonBorder(int x, int y, int w, int h, int radius, int R, int G, int B);

char *fbp = 0;
int fbfd = 0;
long int screenSize = 0;
int screenXsize=0;
int screenYsize=0;
int framebufferBytesPerPixel=4;
int currentX=0;
int currentY=0;
int textSize=1;
int foreColourR=0;
int foreColourG=0;
int foreColourB=0;
int backColourR=0;
int backColourG=0;
int backColourB=0;


void closeScreen(void);
int initScreen(void);
void setPixel(int x, int y, int R, int G, int B);
void clearScreen();
void displayChar(int ch);
void setLargePixel(int x, int y, int size, int R, int G, int B);
void gotoXY(int x, int y);
void setForeColour(int R,int G,int B);
void setBackColour(int R,int G,int B);
void displayStr(char*s);
void displayButton(char*s);
void displayButton2x12(char*s1,char*s2);
void displayButton1x12(char*s1);
void drawLine(int x0, int y0, int x1, int y1,int r,int g,int b);

void displayStr(char*s)
{
 int p;
 p=0;
 do
 {
    displayChar(s[p++]);
 }
 while(s[p]!=0);
}

// ★Shonan_lite-PI4統合版パッチ: 画面全体の文字を周波数表示・ボタンと同じ
// TTFフォント(ttFaceButton、レギュラーウェイト)で統一するため、ドット
// フォント(font[][])の代わりにここでアンチエイリアス描画する。既存コードは
// 「1文字が8*textSize x 9*textSize の固定セルを占め、currentXが8*textSize
// ずつ進む」という等幅前提(空白埋めでの消去、複数displayStr呼び出しでの
// 位置合わせ等)に多数依存しているため、そのセル寸法・前進幅は変えず、
// セル内でグリフを中央寄せ描画するだけに留めている。ttFontButtonReady==0
// (フォント読込失敗)時は元のドットフォント描画にフォールバックする。
void displayChar(int ch)
{
  int row;
  int col;
  int pix;
  int descender;
  int cellW = 8*textSize;
  int cellH = 9*textSize;

  if (ttFontButtonReady)
    {
      int xx, yy;
      // ★セル高(cellH)ちょうどしかクリアしないと、TTFグリフ(セルより大きい
      // pixel_sizeで描画するため)の上端・下端がセルからはみ出し、次に別の
      // 文字へ変わった際そのはみ出し部分だけ消えずに残ることがある
      // (周波数表示のFreeType化で見つかったのと同じ不具合、実機で確認)。
      // 上下に余裕を持ってクリアする。
      int clearMarginY = cellH*3/10;
      for (yy=-clearMarginY; yy<cellH+clearMarginY; yy++)
        {
          for (xx=0; xx<cellW; xx++)
            {
              setPixel(currentX+xx, currentY+yy, backColourR, backColourG, backColourB);
            }
        }
      if (ch != ' ')
        {
          FT_Set_Pixel_Sizes(ttFaceButton, 0, (cellH*8)/7);
          if (FT_Load_Char(ttFaceButton, (FT_ULong)ch, FT_LOAD_RENDER) == 0)
            {
              FT_GlyphSlot g = ttFaceButton->glyph;
              int originX = currentX + (cellW - (int)g->bitmap.width)/2;
              int baselineY = currentY + (cellH*4)/5;
              for (row=0; row<(int)g->bitmap.rows; row++)
                {
                  for (col=0; col<(int)g->bitmap.width; col++)
                    {
                      unsigned char cov = g->bitmap.buffer[row*g->bitmap.pitch+col];
                      if (cov==0) continue;
                      int blR = backColourR + ((foreColourR-backColourR)*cov)/255;
                      int blG = backColourG + ((foreColourG-backColourG)*cov)/255;
                      int blB = backColourB + ((foreColourB-backColourB)*cov)/255;
                      setPixel(originX+col, baselineY - g->bitmap_top + row, blR, blG, blB);
                    }
                }
            }
        }
      currentX = currentX + cellW;
      return;
    }

  if(font[ch][0] & 0x80)
  {
  descender=3*textSize;
  }
  else
  {
  descender=0;
  }

  for(row=0;row<9;row++)
    {
    pix=font[ch][row];
    if(row==0) pix=pix & 0x7F;                //top bit of first row indicates descender
    for(col=0;col<8;col++)
      {
       if((pix << col) & 0x80)
         {
            setLargePixel(currentX+col*textSize,currentY+row*textSize+descender,textSize,foreColourR,foreColourG,foreColourB);
         }
       else
         { 
            setLargePixel(currentX+col*textSize,currentY+row*textSize+descender,textSize,backColourR,backColourG,backColourB);
         }
      }
    }

  currentX=currentX+8*textSize;
}

void clearButton(void)
{
gotoXY(currentX+1,currentY+1);
for(int xi=0;xi<98;xi++)
  {
  for(int yi=0;yi<48;yi++)
    {
    setPixel(currentX+xi,currentY+yi,backColourR,backColourG,backColourB);
    }
  }

}

// ★Shonan_lite-PI4統合版パッチ: ボタン文字・大きな周波数表示で共用するTTF
// フォント(Liberation Sans Bold、apt版fonts-liberation2同梱)を読み込む。
void initTTFont(void)
{
  const char *boldCandidates[] = {
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    NULL
  };
  // ★ボタン文字は太字だと圧迫感があるとのことでレギュラーウェイトを使う。
  const char *regularCandidates[] = {
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    NULL
  };
  int i;

  if (FT_Init_FreeType(&ttLibrary))
    {
      printf("initTTFont: FT_Init_FreeType failed, using dot-matrix font/square buttons\n");
      return;
    }
  for (i = 0; boldCandidates[i] != NULL; i++)
    {
      if (FT_New_Face(ttLibrary, boldCandidates[i], 0, &ttFace) == 0)
        {
          ttFontReady = 1;
          printf("initTTFont: loaded %s\n", boldCandidates[i]);
          break;
        }
    }
  for (i = 0; regularCandidates[i] != NULL; i++)
    {
      if (FT_New_Face(ttLibrary, regularCandidates[i], 0, &ttFaceButton) == 0)
        {
          ttFontButtonReady = 1;
          printf("initTTFont: loaded %s\n", regularCandidates[i]);
          break;
        }
    }
  if (!ttFontReady && !ttFontButtonReady)
    {
      printf("initTTFont: no TTF font found, using dot-matrix font/square buttons\n");
    }
}

// 現在のFT_Set_Pixel_Sizesで指定中のサイズでの文字列描画幅(px)を測る。
static int measureTextTTFFace(FT_Face face, const char *s)
{
  int width = 0;
  int i;
  for (i = 0; s[i] != 0; i++)
    {
      if (FT_Load_Char(face, (FT_ULong)s[i], FT_LOAD_DEFAULT)) continue;
      width += (face->glyph->advance.x >> 6);
    }
  return width;
}

// (x,baselineY)を起点に文字列をアンチエイリアス描画する。backColourR/G/Bと
// のブレンドでカバレッジ(0-255)を滑らかにする(displayFreqTTFのグリフ描画と
// 同じ考え方)。
static void drawTextTTFFace(FT_Face face, const char *s, int x, int baselineY, int R, int G, int B)
{
  int penX = x;
  int i, row, col;
  for (i = 0; s[i] != 0; i++)
    {
      if (FT_Load_Char(face, (FT_ULong)s[i], FT_LOAD_RENDER)) continue;
      FT_GlyphSlot g = face->glyph;
      for (row = 0; row < (int)g->bitmap.rows; row++)
        {
          for (col = 0; col < (int)g->bitmap.width; col++)
            {
              unsigned char cov = g->bitmap.buffer[row * g->bitmap.pitch + col];
              if (cov == 0) continue;
              int blR = backColourR + ((R - backColourR) * cov) / 255;
              int blG = backColourG + ((G - backColourG) * cov) / 255;
              int blB = backColourB + ((B - backColourB) * cov) / 255;
              setPixel(penX + g->bitmap_left + col, baselineY - g->bitmap_top + row, blR, blG, blB);
            }
        }
      penX += (g->advance.x >> 6);
    }
}

// 角丸ボタン枠(1px)を描画する。直線部は角の半径分だけ内側にとどめ、4隅は
// 三角関数で四分円を描く(高さ・幅とも小さいボタンなので負荷は無視できる)。
static void drawRoundedButtonBorder(int x, int y, int w, int h, int radius, int R, int G, int B)
{
  int i, a;
  for (i = x + radius; i <= x + w - radius; i++)
    {
      setPixel(i, y, R, G, B);
      setPixel(i, y + h, R, G, B);
    }
  for (i = y + radius; i <= y + h - radius; i++)
    {
      setPixel(x, i, R, G, B);
      setPixel(x + w, i, R, G, B);
    }
  for (a = 0; a <= 90; a++)
    {
      double rad = a * M_PI / 180.0;
      int dx = (int)(radius * cos(rad) + 0.5);
      int dy = (int)(radius * sin(rad) + 0.5);
      setPixel(x + radius - dx, y + radius - dy, R, G, B);
      setPixel(x + w - radius + dx, y + radius - dy, R, G, B);
      setPixel(x + radius - dx, y + h - radius + dy, R, G, B);
      setPixel(x + w - radius + dx, y + h - radius + dy, R, G, B);
    }
}

void displayButton(char*s)
{
int saveX=currentX;
int saveY=currentY;

gotoXY(saveX,saveY);
clearButton();
// ★Shonan_lite-PI4統合版パッチ: 角丸ボタン枠+TTFアンチエイリアス文字に変更。
// ttFontReady==0(フォント読込失敗)時は元の直角枠+ドットフォントへ戻る。
drawRoundedButtonBorder(saveX,saveY,100,50,0,foreColourR,foreColourG,foreColourB);
if (ttFontButtonReady)
  {
    FT_Set_Pixel_Sizes(ttFaceButton,0,23);
    int tw=measureTextTTFFace(ttFaceButton,s);
    drawTextTTFFace(ttFaceButton,s,saveX+(100-tw)/2,saveY+33,foreColourR,foreColourG,foreColourB);
  }
else
  {
    int sx=50-((strlen(s)*16)/2);
    gotoXY(saveX+sx,saveY+18);
    textSize=2;
    displayStr(s);
  }
currentX=saveX+105;
currentY=saveY;

}

void displayButton2x12(char*s1,char*s2)
{
int saveX=currentX;
int saveY=currentY;

gotoXY(saveX,saveY);
clearButton();
drawRoundedButtonBorder(saveX,saveY,100,50,0,foreColourR,foreColourG,foreColourB);
if (ttFontButtonReady)
  {
    FT_Set_Pixel_Sizes(ttFaceButton,0,12);
    int tw1=measureTextTTFFace(ttFaceButton,s1);
    drawTextTTFFace(ttFaceButton,s1,saveX+(100-tw1)/2,saveY+22,foreColourR,foreColourG,foreColourB);
    int tw2=measureTextTTFFace(ttFaceButton,s2);
    drawTextTTFFace(ttFaceButton,s2,saveX+(100-tw2)/2,saveY+38,foreColourR,foreColourG,foreColourB);
  }
else
  {
    int sx=50-((strlen(s1)*8)/2);
    gotoXY(saveX+sx,saveY+11);
    textSize=1;
    displayStr(s1);
    sx=50-((strlen(s2)*8)/2);
    gotoXY(saveX+sx,saveY+29);
    textSize=1;
    displayStr(s2);
  }
currentX=saveX+105;
currentY=saveY;
}

void displayButton1x12(char*s1)
{
int saveX=currentX;
int saveY=currentY;

gotoXY(saveX,saveY);
clearButton();
drawRoundedButtonBorder(saveX,saveY,100,50,0,foreColourR,foreColourG,foreColourB);
if (ttFontButtonReady)
  {
    FT_Set_Pixel_Sizes(ttFaceButton,0,14);
    int tw=measureTextTTFFace(ttFaceButton,s1);
    drawTextTTFFace(ttFaceButton,s1,saveX+(100-tw)/2,saveY+31,foreColourR,foreColourG,foreColourB);
  }
else
  {
    int sx=50-((strlen(s1)*8)/2);
    gotoXY(saveX+sx,saveY+20);
    textSize=1;
    displayStr(s1);
  }
currentX=saveX+105;
currentY=saveY;
}



void gotoXY(int x, int y)
{
currentX=x;
currentY=y;
}

void setForeColour(int R,int G,int B)
{
foreColourR=R;
foreColourG=G;
foreColourB=B;
}

void setBackColour(int R,int G,int B)
{
backColourR=R;
backColourG=G;
backColourB=B;
}

void clearScreen()
{
  for(int y=0;y<screenYsize;y++)
	  {
      for(int x=0;x<screenXsize;x++)
        {
        setPixel(x,y,backColourR,backColourG,backColourB);
        }
  	}
}

void setPixel(int x, int y, int R, int G, int B)
{
if(x>=0 && y>=0 && x<screenXsize && y<screenYsize)
  {
  int p=(x+screenXsize*y)*framebufferBytesPerPixel;
  if (framebufferBytesPerPixel == 2)
    {
      // KMS commonly exposes the DFR0550 as RGB565 (16 bits per pixel).
      uint16_t pixel = (uint16_t)(((R & 0xf8) << 8) |
                                  ((G & 0xfc) << 3) |
                                  ((B & 0xf8) >> 3));
      memcpy(fbp+p, &pixel, sizeof(pixel));
    }
  else
    {
      memset(fbp+p,B,1);      //Blue
      memset(fbp+p+1,G,1);    //Green
      memset(fbp+p+2,R,1);    //Red
      memset(fbp+p+3,0x80,1); //A
    }
  }

}

void drawLine(int x0, int y0, int x1, int y1,int r,int g,int b) {
 
  int dx = abs(x1-x0), sx = x0<x1 ? 1 : -1;
  int dy = abs(y1-y0), sy = y0<y1 ? 1 : -1; 
  int err = (dx>dy ? dx : -dy)/2, e2;
 
  for(;;){
    setPixel(x0,y0,r,g,b);
    if (x0==x1 && y0==y1) break;
    e2 = err;
    if (e2 >-dx) { err -= dy; x0 += sx; }
    if (e2 < dy) { err += dx; y0 += sy; }
  }
}

void setLargePixel(int x, int y, int size, int R, int G, int B)
{
  for (int px=0;px<size;px++)
    {
      for(int py=0;py<size;py++)
        {
        setPixel(x+px,y+py,R,G,B);
        }
    }
}

void closeScreen(void)
{
  munmap(fbp, screenSize);
  close(fbfd);
}


int initScreen(void)
{

  struct fb_var_screeninfo vinfo;
  struct fb_fix_screeninfo finfo;
 
  fbfd = open("/dev/fb0", O_RDWR);
  if (fbfd < 0)
  {
    printf("Error: cannot open framebuffer device.\n");
    return(0);
  }

  if (ioctl(fbfd, FBIOGET_FSCREENINFO, &finfo)) 
  {
    printf("Error reading fixed information.\n");
    return(0);
  }



  if (ioctl(fbfd, FBIOGET_VSCREENINFO, &vinfo)) 
  {
    printf("Error reading variable information.\n");
    return(0);
  }
  
  screenXsize=vinfo.xres;
  screenYsize=vinfo.yres;
  framebufferBytesPerPixel = (vinfo.bits_per_pixel + 7) / 8;
  if (framebufferBytesPerPixel != 2 && framebufferBytesPerPixel != 4)
  {
    printf("Error: unsupported framebuffer depth: %u bits.\n", vinfo.bits_per_pixel);
    return(0);
  }
  
  screenSize = finfo.smem_len;
  fbp = (char*)mmap(0, screenSize, PROT_READ | PROT_WRITE, MAP_SHARED, fbfd, 0);
                    
   if ((int)fbp == -1) 
   {
    return 0;
   }
  else 
   {
    return 1;
   }
}
