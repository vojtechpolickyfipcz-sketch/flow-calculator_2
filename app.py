# 1. INSTALACE A IMPORTY
!pip install numpy matplotlib pandas ipywidgets

import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import ipywidgets as widgets
from IPython.display import display, clear_output

# --- 2. FYZIKÁLNÍ JÁDRO ---
def calculate_dp(v_type, d_min, d_max, pitch, L_mm, flow_lmin, density, viscosity):
    flow_m3s = flow_lmin / (60 * 1000)
    d_min_m = d_min / 1000
    L_m = L_mm / 1000
    area = np.pi * (d_min_m / 2)**2
    v_velocity = flow_m3s / area
    Re = (density * v_velocity * d_min_m) / viscosity
    l_smooth = np.array([(64/r if r < 2300 else 0.3164/r**0.25) for r in Re])
    
    if v_type == "Vlnitá":
        rel_rough = (d_max - d_min) / (2 * d_min)
        p_m = pitch / 1000
        corr_factor = 1 + (rel_rough * 12) * (0.004 / p_m)
        l_final = l_smooth * max(corr_factor, 3.2)
    else:
        l_final = l_smooth
        
    dp_pa = l_final * (L_m / d_min_m) * (density * v_velocity**2 / 2)
    return dp_pa / 1000 

# --- 3. KONSTRUKCE INTERAKTIVNÍHO ROZHRANÍ ---
# Zvětšená šířka pro popisky i samotná pole
style = {'description_width': '180px'}
wide_layout = widgets.Layout(width='500px') 
short_layout = widgets.Layout(width='410px') # Pro hustotu, aby zbylo místo na jednotku

# A) Identifikace a Médium
w_fluid_name = widgets.Text(value='G12+ Specifikace', description='Název kapaliny:', style=style, layout=wide_layout)
w_temp = widgets.FloatText(value=22.0, description='Teplota měření [°C]:', style=style, layout=wide_layout)

# B) Hustota s volbou jednotek (celková šířka cca 500px)
w_dens_val = widgets.FloatText(value=1060.0, description='Hustota:', style=style, layout=short_layout)
w_dens_unit = widgets.Dropdown(options=['kg/m³', 'g/cm³'], value='kg/m³', layout=widgets.Layout(width='90px'))
w_dens_box = widgets.HBox([w_dens_val, w_dens_unit])

# C) Ostatní parametry
w_visc = widgets.FloatText(value=0.0030, step=0.0001, description='Viskozita [Pa·s]:', style=style, layout=wide_layout)
w_L = widgets.FloatText(value=500.00, step=0.01, description='Délka trasy [mm]:', style=style, layout=wide_layout)
w_flow = widgets.FloatSlider(value=25.0, min=0.5, max=100.0, step=0.5, description='Max Průtok [l/min]:', style=style, layout=wide_layout)

def create_variant_box(i):
    header = widgets.HTML(f"<b style='color:#1565c0; font-size:14px;'>Varianta {i+1}</b>")
    t_drop = widgets.Dropdown(options=['Hladká', 'Vlnitá'], value='Vlnitá' if i > 0 else 'Hladká', description='Typ potrubí:', style=style, layout=widgets.Layout(width='95%'))
    d_min = widgets.FloatText(value=12.00, step=0.01, description='Vnitřní Ø [mm]:', style=style, layout=widgets.Layout(width='95%'))
    d_max = widgets.FloatText(value=15.00, step=0.01, description='Maximální Ø [mm]:', style=style, layout=widgets.Layout(width='95%'))
    p_drop = widgets.Dropdown(options=[3.1, 3.3, 3.7, 4.0, 4.65], value=3.7, description='Rozteč [mm]:', style=style, layout=widgets.Layout(width='95%'))
    
    def toggle_fields(change):
        is_smooth = (change['new'] == 'Hladká')
        d_max.disabled = is_smooth
        p_drop.disabled = is_smooth
    t_drop.observe(toggle_fields, names='value')
    
    if t_drop.value == 'Hladká':
        d_max.disabled = True
        p_drop.disabled = True

    return widgets.VBox([header, t_drop, d_min, d_max, p_drop], 
                        layout=widgets.Layout(border='2px solid #e0e0e0', padding='10px', margin='5px', width='24%', border_radius='10px')), t_drop, d_min, d_max, p_drop

# Sestavení UI
v_boxes, v_inputs = [], []
for i in range(4):
    box, t, dm, dmax, p = create_variant_box(i)
    v_boxes.append(box)
    v_inputs.append({'type': t, 'd_min': dm, 'd_max': dmax, 'pitch': p})

btn_calc = widgets.Button(description="📊 GENEROVAT TECHNICKÝ REPORT", button_style='primary', layout=widgets.Layout(width='99%', height='50px', margin='20px 0px'))
output = widgets.Output()

def on_button_clicked(b):
    with output:
        clear_output(wait=True)
        final_density = w_dens_val.value * 1000 if w_dens_unit.value == 'g/cm³' else w_dens_val.value
        flow_axis = np.linspace(0.1, w_flow.value, 100)
        plt.figure(figsize=(15, 7))
        results_list = []
        
        for i, v in enumerate(v_inputs):
            dp_curve = calculate_dp(v['type'].value, v['d_min'].value, v['d_max'].value, v['pitch'].value, 
                                    w_L.value, flow_axis, final_density, w_visc.value)
            plt.plot(flow_axis, dp_curve, lw=3, label=f"Var {i+1}: {v['type'].value}")
            results_list.append({
                "ID": f"Var {i+1}",
                "Konfigurace": f"Ø{v['d_min'].value:.2f}" if v['type'].value == "Hladká" else f"Ø{v['d_min'].value:.2f}/Ø{v['d_max'].value:.2f} p{v['pitch'].value}",
                "Ztráta [kPa]": dp_curve[-1]
            })

        plt.title(f"REPORT: {w_fluid_name.value} ({final_density} kg/m³ @ {w_temp.value}°C)", fontsize=14, fontweight='bold')
        plt.xlabel("Průtok [l/min]")
        plt.ylabel("Tlaková ztráta [kPa]")
        plt.legend()
        plt.grid(True, alpha=0.5)
        plt.show()
        
        df = pd.DataFrame(results_list)
        ref_val = df.iloc[0]["Ztráta [kPa]"]
        df["Ztráta [kPa]"] = df["Ztráta [kPa]"].map('{:.3f}'.format)
        df["Rozdíl k Var 1"] = df["Ztráta [kPa]"].astype(float).apply(lambda x: f"{((x/ref_val)-1)*100:+.2f} %" if ref_val > 0 else "0.00 %")
        
        print(f"REPORT PRO KAPALINU: {w_fluid_name.value}")
        print(f"Podmínky měření: {w_temp.value} °C | Hustota: {final_density} kg/m³ | Viskozita: {w_visc.value} Pa·s\n")
        display(df)

btn_calc.on_click(on_button_clicked)

display(widgets.HTML("<h1 style='color:#0d47a1; font-family:Arial;'>Hydraulický Srovnávač 4.1</h1>"))
display(widgets.VBox([
    widgets.HBox([w_fluid_name]),
    widgets.HBox([w_temp]),
    widgets.HBox([w_dens_box]),
    widgets.HBox([w_visc]),
    widgets.HBox([w_L]),
    widgets.HBox([w_flow])
]))
display(widgets.HBox(v_boxes))
display(btn_calc)
display(output)