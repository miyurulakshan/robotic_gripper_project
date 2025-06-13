# File: interactive_gripper_visualization.py
# A unified, high-performance visualization class for real-time control.

import pygame

class InteractiveGripperVisualizer:
    """
    Manages a single, combined Pygame window with interactive controls and a detailed FSR monitor.
    Optimized for high-speed, real-time updates.
    """
    def __init__(self):
        # --- Window Settings (Increased height for the combined view) ---
        self.width, self.height = 1000, 850
        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption("Robotic Gripper Control & Force Monitor")

        # --- Fonts (Initialized once) ---
        self.title_font = pygame.font.Font(None, 50)
        self.button_font = pygame.font.Font(None, 40)
        self.status_font = pygame.font.Font(None, 36)
        self.info_font = pygame.font.Font(None, 28)
        self.fsr_label_font = pygame.font.Font(None, 28)
        self.fsr_value_font = pygame.font.Font(None, 22)

        # --- Colors ---
        self.colors = {'bg':(25,35,45),'gripper_base':(80,90,110),'gripper_jaw':(120,130,150),'gripper_jaw_face':(100,110,130),'text':(230,230,240),'btn_normal':(0,120,215),'btn_hover':(0,140,255),'btn_emergency':(200,0,0),'btn_emergency_hover':(255,50,50),'status_ok':(0,200,100),'status_active':(255,170,0),'status_fail':(220,40,40),'fsr_jaw_bg':(40,50,65),'cof_color':(255,255,0)}

        # --- Button Definitions ---
        self.buttons = {'grab':pygame.Rect(50,500,150,60),'release':pygame.Rect(220,500,150,60),'emergency':pygame.Rect(self.width-200,500,150,60)}

    def _get_glow_color(self, v, max_v=1023):
        r=min(v/max_v,1.0); return (0,int(510*r),255) if r<0.5 else (int(510*(r-0.5)),int(255*(1-(r-0.5)*2)),0)
    
    def _calculate_cof(self, coords, values):
        tf=sum(values); return None if tf==0 else (sum(c[0]*f for c,f in zip(coords,values))/tf,sum(c[1]*f for c,f in zip(coords,values))/tf)

    def _draw_text(self, text, font, color, center_pos):
        s=font.render(text,True,color); r=s.get_rect(center=center_pos); self.screen.blit(s,r)

    def _draw_gripper(self, angle):
        br=pygame.Rect(0,0,150,80); br.center=(self.width/2,120); pygame.draw.rect(self.screen,self.colors['gripper_base'],br,border_radius=10)
        jw,jh,jd=120,250,20; oo,co=80,10; cofs=oo-((angle/100.0)*(oo-co))
        for s in ['left','right']:
            jx=(self.width/2)-jw-cofs if s=='left' else (self.width/2)+cofs; jy=br.bottom
            pygame.draw.rect(self.screen,self.colors['gripper_jaw'],(jx,jy,jw,jh),border_radius=8)
            p=[(jx,jy),(jx+jd,jy-jd),(jx+jd,jy+jh-jd),(jx,jy+jh)] if s=='left' else [(jx+jw,jy),(jx+jw-jd,jy-jd),(jx+jw-jd,jy+jh-jd),(jx+jw,jy+jh)]
            pygame.draw.polygon(self.screen,self.colors['gripper_jaw_face'],p)

    def _draw_fsr_details(self, fsr_values):
        self._draw_text("Force Sensor Monitor",self.title_font,self.colors['text'],center_pos=(self.width/2,620))
        jw,jh=150,180; ljr=pygame.Rect(250,660,jw,jh); rjr=pygame.Rect(self.width-250-jw,660,jw,jh)
        pp=[(jw/2,30+i*40) for i in range(4)]
        jd=[("Left",ljr,fsr_values[0:4]),("Right",rjr,fsr_values[4:8])]
        for n,jr,v in jd:
            pygame.draw.rect(self.screen,self.colors['fsr_jaw_bg'],jr,border_radius=15)
            self._draw_text(n+" Jaw",self.fsr_label_font,self.colors['text'],center_pos=(jr.centerx,jr.top-15))
            pc=[(jr.x+x,jr.y+y) for x,y in pp]
            for i,val in enumerate(v):
                pos=pc[i]; br=20; dr=int((val/1023)*25)
                if dr>1: gc=self._get_glow_color(val); s=pygame.Surface((dr*2,dr*2),pygame.SRCALPHA); pygame.draw.circle(s,(*gc,100),(dr,dr),dr); self.screen.blit(s,(pos[0]-dr,pos[1]-dr))
                pygame.draw.circle(self.screen,self.colors['text'],pos,15)
                self._draw_text(str(val),self.fsr_value_font,self.colors['bg'],center_pos=pos)
            cof=self._calculate_cof(pc,v)
            if cof: x,y=int(cof[0]),int(cof[1]); pygame.draw.line(self.screen,self.colors['cof_color'],(x-10,y),(x+10,y),2); pygame.draw.line(self.screen,self.colors['cof_color'],(x,y-10),(x,y+10),2)

    def update(self, angle, state, fsr_values, object_detected):
        self.screen.fill(self.colors['bg'])
        self._draw_gripper(angle)
        self._draw_text("Robotic Gripper Control",self.title_font,self.colors['text'],center_pos=(self.width/2,40))
        sc=self.colors['status_ok'];
        if "GRABBING" in state or "RELEASING" in state: sc=self.colors['status_active']
        elif "FAIL" in state or "EMERGENCY" in state: sc=self.colors['status_fail']
        self._draw_text(f"Status: {state}",self.status_font,sc,center_pos=(self.width/2,450))
        self._draw_text(f"Angle: {angle}°",self.info_font,self.colors['text'],center_pos=(self.width/2,490))
        mp=pygame.mouse.get_pos()
        for n,r in self.buttons.items():
            h=r.collidepoint(mp); ck=f'btn_{n}_hover' if h and n=='emergency' else 'btn_hover' if h else f'btn_{n}' if n=='emergency' else 'btn_normal'
            pygame.draw.rect(self.screen,self.colors[ck],r,border_radius=10)
            self._draw_text(n.upper(),self.button_font,self.colors['text'],center_pos=r.center)
        pygame.draw.line(self.screen,self.colors['gripper_base'],(50,580),(self.width-50,580),3)
        self._draw_fsr_details(fsr_values)

    def check_events(self, events):
        for event in events:
            if event.type == pygame.QUIT: return "quit"
            if event.type == pygame.MOUSEBUTTONDOWN and event.button==1:
                for name,rect in self.buttons.items():
                    if rect.collidepoint(event.pos): return name
        return None
