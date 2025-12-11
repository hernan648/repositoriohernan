import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import re
# No necesitamos ipywidgets ni IPython.display aquí

# ---------------------------------------------------------
# FUNCIÓN DE CÁLCULO DE PUNTAJE (AHORA GLOBAL EN STREAMLIT)
# ---------------------------------------------------------
def calcular_puntaje(row):
    # A. Servicio (30%): Tope 15 años (180 meses)
    m_serv = row['Antigüedad en el servicio (meses)']
    raw_serv = 0
    if m_serv >= 24 and m_serv <= 60:
        raw_serv = 20
    elif m_serv >= 61 and m_serv <= 96:
        raw_serv = 40
    elif m_serv >= 97 and m_serv <= 132:
        raw_serv = 60
    elif m_serv >= 133 and m_serv <= 168:
        raw_serv = 80
    elif m_serv >= 169:
        raw_serv = 100
    # Si es menos de 24 meses, raw_serv se mantiene en 0
    p_serv = raw_serv * 0.30

    # B. Grado (15%): Tope 10 años (120 meses)
    m_grad = row['Antigüedad en el grado (meses)']
    raw_grad = 0
    if m_grad >= 12 and m_grad <= 24:
        raw_grad = 20
    elif m_grad >= 25 and m_grad <= 48:
        raw_grad = 40
    elif m_grad >= 49 and m_grad <= 72:
        raw_grad = 60
    elif m_grad >= 73 and m_grad <= 96:
        raw_grad = 80
    elif m_grad >= 97:
        raw_grad = 100
    # Si es menos de 12 meses, raw_grad se mantiene en 0
    p_grad = raw_grad * 0.15

    # C. Equidad (30%): Depende del Estamento y Grado
    estamento_actual = row['Estamento']
    grado_actual = row['Grado']
    raw_eq = 0 # Default

    # *** REGLAS DE EQUIDAD SEGÚN criterios.png ***
    if estamento_actual == 'PROFESIONAL':
        if grado_actual == 5 or grado_actual == 6:
            raw_eq = 0
        elif grado_actual == 7 or grado_actual == 8:
            raw_eq = 20
        elif grado_actual == 9:
            raw_eq = 40
        elif grado_actual == 10:
            raw_eq = 60
        elif grado_actual == 11:
            raw_eq = 80
        elif grado_actual == 12:
            raw_eq = 100
    elif estamento_actual == 'TECNICO':
        if grado_actual == 10:
            raw_eq = 0
        elif grado_actual == 11:
            raw_eq = 20
        elif grado_actual == 12:
            raw_eq = 40
        elif grado_actual == 13:
            raw_eq = 60
        elif grado_actual == 14:
            raw_eq = 80
        elif grado_actual == 15:
            raw_eq = 100
    elif estamento_actual == 'ADMINISTRATIVO':
        if grado_actual == 11:
            raw_eq = 0
        elif grado_actual == 12:
            raw_eq = 20
        elif grado_actual == 13:
            raw_eq = 40
        elif grado_actual == 14:
            raw_eq = 60
        elif grado_actual == 15:
            raw_eq = 80
        elif grado_actual == 16:
            raw_eq = 100
    else:
        raw_eq = 0 # Valor por defecto para estamentos y grados no especificados
    p_eq = raw_eq * 0.30

    # D. Calificación (25%): Fija
    try:
        val_calif = row['Puntaje Calificación 2024-2025']
    except:
        val_calif = 100 # Default si falla
    p_cal = val_calif * 0.25

    total_puntaje = p_serv + p_grad + p_eq + p_cal
    return pd.Series({
        'Puntaje_Simulado': total_puntaje,
        'Puntaje_Servicio': p_serv,
        'Puntaje_Grado': p_grad,
        'Puntaje_Equidad': p_eq,
        'Puntaje_Calificacion': p_cal
    })

# ---------------------------------------------------------
# 2. LÓGICA DE SIMULACIÓN (MOTOR)
# ---------------------------------------------------------
def ejecutar_simulacion_streamlit(df_input, nombre_seleccionado, cupos_anuales):
    # Replicar la estructura de tu ejecutar_simulacion, pero adaptada para no depender de df global
    # y con la duración de 30 años y múltiples ascensos

    # Aseguramos que df_input sea una copia para no modificar el original
    df_sim = df_input.copy()

    target_row = df_sim[df_sim['Nombre_Completo'] == nombre_seleccionado]

    if target_row.empty:
        return None, [], "Funcionario no encontrado.", []

    estamento = target_row.iloc[0]['Estamento']
    id_target = target_row.index[0] # Usar el índice original para rastrear

    congelados = []
    historia_ranking = []
    all_yearly_ascended = [] # Para almacenar solo los ascendidos de cada año

    max_anios = 30 # Simular 30 años
    ascenso_years = []
    score_cols = ['Puntaje_Simulado', 'Puntaje_Servicio', 'Puntaje_Grado', 'Puntaje_Equidad', 'Puntaje_Calificacion']

    # Añadir 'ID' si no existe (para rastrear a los funcionarios)
    if 'ID' not in df_sim.columns:
        df_sim['ID'] = df_sim.index

    # Calcular puntajes iniciales para Año 0
    df_sim[score_cols] = df_sim.apply(calcular_puntaje, axis=1)
    df_sim = df_sim.sort_values('Puntaje_Simulado', ascending=False).reset_index(drop=True)

    if id_target not in df_sim['ID'].values:
        return None, [], "Funcionario no encontrado en el pool inicial.", []

    pos_inicial_plot = df_sim[df_sim['ID'] == id_target].index[0] + 1
    historia_ranking.append((0, pos_inicial_plot))

    # Procesar ascenso inicial si corresponde (Año 0)
    if pos_inicial_plot <= cupos_anuales: 
        ascenso_years.append(0)

        target_ascended_data = df_sim[df_sim['ID'] == id_target].iloc[0].copy()
        if target_ascended_data['Grado'] > 5: # Asumo que el grado más bajo que asciende es 5
            target_ascended_data['Grado'] -= 1
        else:
            target_ascended_data['Grado'] = 5 # Mínimo grado 5
        target_ascended_data['Antigüedad en el grado (meses)'] = 24
        target_ascended_data['Antigüedad en el servicio (meses)'] += 24

        congelados.append({'data': target_ascended_data, 'anio_retorno': 0 + 2})
        df_sim = df_sim[df_sim['ID'] != id_target].copy()

    # Bucle de simulación para Año 1 a max_anios
    for anio_sim in range(1, max_anios + 1):
        # 1. Envejecer (+12 meses)
        df_sim['Antigüedad en el servicio (meses)'] += 12
        df_sim['Antigüedad en el grado (meses)'] += 12

        # 2. Gestionar Retornos
        vuelven = [x for x in congelados if x['anio_retorno'] == anio_sim]
        congelados = [x for x in congelados if x['anio_retorno'] != anio_sim]

        if vuelven:
            rows_vuelven = pd.DataFrame([x['data'] for x in vuelven])
            df_sim = pd.concat([df_sim, rows_vuelven], ignore_index=True)

        # 3. Recalcular y Ordenar
        df_sim[score_cols] = df_sim.apply(calcular_puntaje, axis=1)
        df_sim = df_sim.sort_values('Puntaje_Simulado', ascending=False).reset_index(drop=True)

        # 4. Buscar al funcionario
        idx_encontrado = df_sim.index[df_sim['ID'] == id_target].tolist()

        if idx_encontrado:
            pos_actual = idx_encontrado[0] + 1
            historia_ranking.append((anio_sim, pos_actual))

            if pos_actual <= cupos_anuales: 
                ascenso_years.append(anio_sim)

                target_ascended_data = df_sim[df_sim['ID'] == id_target].iloc[0].copy()
                if target_ascended_data['Grado'] > 5: # Asumo que el grado más bajo que asciende es 5
                    target_ascended_data['Grado'] -= 1
                else:
                    target_ascended_data['Grado'] = 5
                target_ascended_data['Antigüedad en el grado (meses)'] = 24
                target_ascended_data['Antigüedad en el servicio (meses)'] += 24

                congelados.append({'data': target_ascended_data, 'anio_retorno': anio_sim + 2})
                df_sim = df_sim[df_sim['ID'] != id_target].copy()
        else:
            historia_ranking.append((anio_sim, np.nan))

        # 5. Ejecutar Ascensos (Sacar top N)
        num_ascensos_a_ejecutar = min(cupos_anuales, len(df_sim))
        ascendidos_this_year = df_sim.iloc[:num_ascensos_a_ejecutar].copy()
        df_sim = df_sim.iloc[num_ascensos_a_ejecutar:].copy()

        for _, row in ascended_this_year.iterrows():
            return_data = row.copy()
            if return_data['Grado'] > 5:
                return_data['Grado'] -= 1
            else:
                return_data['Grado'] = 5
            return_data['Antigüedad en el grado (meses)'] = 24
            congelados.append({'data': return_data, 'anio_retorno': anio_sim + 2})
        
        all_yearly_ascended.append((anio_sim, ascended_this_year[['Nombre_Completo', 'Puntaje_Simulado', 'Puntaje_Servicio', 'Puntaje_Grado', 'Puntaje_Equidad', 'Puntaje_Calificacion', 'Antigüedad en el servicio (meses)', 'Antigüedad en el grado (meses)', 'Grado']].copy()))

    return historia_ranking, ascenso_years, estamento, all_yearly_ascended

# ---------------------------------------------------------
# STREAMLIT APP
# ---------------------------------------------------------

st.set_page_config(layout="wide")
st.title('📊 Simulador Interactivo de Ascensos (Ranking)')

# Carga de archivo CSV/Excel
st.sidebar.header("Cargar Archivo de Ranking")
uploaded_file = st.sidebar.file_uploader("Sube tu archivo 'Ranking (1).xlsx' o '.csv'", type=["xlsx", "csv"])

df_main = pd.DataFrame()
if uploaded_file is not None:
    try:
        if uploaded_file.name.endswith('.csv'):
            df_main = pd.read_csv(uploaded_file)
        else:
            df_main = pd.read_excel(uploaded_file)
        
        # Limpieza de columnas
        df_main.columns = [re.sub(r'\s+', ' ', c).strip() for c in df_main.columns]
        
        # --- VERIFICACIÓN DE COLUMNAS ESENCIALES ---
        required_cols = [
            'Apellido Paterno', 'Apellido Materno', 'Nombres', # Para Nombre_Completo
            'Estamento', 'Grado', 'Antigüedad en el servicio (meses)', 
            'Antigüedad en el grado (meses)', 'Puntaje Calificación 2024-2025', # Para calcular_puntaje y simulación
            'Puntaje total' # Para ordenamiento inicial
        ]

        missing_cols = [col for col in required_cols if col not in df_main.columns]
        if missing_cols:
            st.error(f"⚠️ ERROR: Faltan columnas esenciales en tu archivo. \nColumnas requeridas: {required_cols}\nColumnas encontradas: {list(df_main.columns)}\nPor favor, asegúrate de que tu archivo contenga todas las columnas con los nombres exactos.")
            df_main = pd.DataFrame() # Vaciar df_main para detener la simulación
        else:
            # Continuar con el procesamiento si las columnas están presentes
            df_main['Nombre_Completo'] = df_main['Apellido Paterno'] + " " + df_main['Apellido Materno'] + " " + df_main['Nombres']
            df_main = df_main.sort_values('Puntaje total', ascending=False).reset_index(drop=True)

    except Exception as e:
        st.error(f"⚠️ ERROR al cargar el archivo o procesar datos: {e}")

if not df_main.empty:
    st.sidebar.header("Parámetros de Simulación")

    # Widgets Streamlit
    nombre_seleccionado = st.sidebar.selectbox(
        '👤 Selecciona un Funcionario:',
        sorted(df_main['Nombre_Completo'].unique()),
        index=sorted(df_main['Nombre_Completo'].unique()).index("BARRIA ARAYA HERNAN EDUARDO") if "BARRIA ARAYA HERNAN EDUARDO" in df_main['Nombre_Completo'].values else 0
    )

    cupos_anuales = st.sidebar.slider(
        '🚀 Ascensos/Año:',
        min_value=1,
        max_value=20,
        value=5,
        step=1
    )

    # Ejecutar simulación
    historia, ascenso_years, estamento, all_yearly_ascended = ejecutar_simulacion_streamlit(df_main, nombre_seleccionado, cupos_anuales)

    if historia is None:
        st.warning("Error en la simulación o funcionario no encontrado.")
    else:
        st.subheader("--- Ranking Inicial (Puntaje Total original) ---")
        st.dataframe(df_main[['Nombre_Completo', 'Puntaje total', 'Antigüedad en el servicio (meses)', 'Antigüedad en el grado (meses)', 'Grado']].head(10))

        st.subheader("Gráfico de Posición en Ranking")
        x_vals = [h[0] for h in historia]
        y_vals = [h[1] for h in historia]

        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(x_vals, y_vals, marker='o', linewidth=3, color='#1f77b4', label='Posición en Ranking')
        ax.axhline(y=cupos_anuales, color='green', linestyle='--', linewidth=2, label=f'Zona de Ascenso (Top {cupos_anuales})')

        ax.invert_yaxis()
        ax.set_title(f'Simulación de Carrera: {nombre_seleccionado}\nEstamento: {estamento}', fontsize=14, fontweight='bold')
        ax.set_xlabel('Años Transcurridos', fontsize=12)
        ax.set_ylabel('Posición en el Ranking', fontsize=12)
        ax.grid(True, alpha=0.3)
        ax.legend()
        ax.set_xticks(x_vals) # Asegurar unidades enteras

        for x, y in zip(x_vals, y_vals):
            if not pd.isna(y):
                ax.text(x, y, str(int(y)), ha='center', va='bottom', fontsize=9, color='darkblue')

        if ascenso_years:
            for anio in ascenso_years:
                y_at_ascent = None
                for i in range(len(x_vals)):
                    if x_vals[i] == anio:
                        y_at_ascent = y_vals[i]
                        break
                if y_at_ascent is None or pd.isna(y_at_ascent): 
                    y_at_ascent = cupos_anuales # Posición por defecto para el marcador si está NaN
                
                ax.plot(anio, y_at_ascent, 'r*', markersize=15)
                ax.text(anio, y_at_ascent - (0.05 * ax.get_ylim()[0]), f' ¡ASCENSO\n AÑO {anio}!', color='red', fontweight='bold', ha='left', va='top', fontsize=10)
            
            st.success(f"✅ RESULTADO: Con {cupos_anuales} ascensos por año, lograrías subir en los AÑOS: {', '.join(map(str, ascenso_years))}.")
        else:
            st.warning(f"❌ RESULTADO: Con {cupos_anuales} ascensos por año, NO logras ascender en los próximos {max_anios} años.")

        st.pyplot(fig)

        st.subheader("Tablas de Ascensos Anuales")
        if all_yearly_ascended:
            for anio, ascended_df in all_yearly_ascended:
                if not ascended_df.empty:
                    st.markdown(f"**--- Ascensos del Año {anio} ---**")
                    display_cols = ['Nombre_Completo', 'Puntaje_Simulado', 'Puntaje_Servicio', 'Puntaje_Grado', 'Puntaje_Equidad', 'Puntaje_Calificacion', 'Antigüedad en el servicio (meses)', 'Antigüedad en el grado (meses)', 'Grado']
                    st.dataframe(ascended_df[display_cols])
                else:
                    st.markdown(f"**--- Ascensos del Año {anio} ---**")
                    st.info("No hubo ascensos en este año.")

else:
    st.info("Por favor, sube tu archivo de ranking para comenzar la simulación.")


# Para ejecutar esta aplicación Streamlit:
# 1. Guarda el código anterior en un archivo llamado `app.py`.
# 2. Abre tu terminal, navega hasta la carpeta donde guardaste `app.py`.
# 3. Ejecuta `streamlit run app.py`