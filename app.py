import json
import toml
import pytz #what is used for?
import boto3
import base64
import random
import hashlib
import requests
import unidecode #what is used for
import pandas as pd #what is used for
from io import BytesIO #what is used for
import streamlit as st
from unidecode import unidecode
from email.mime.text import MIMEText #este es de mail
from botocore.exceptions import ClientError #Este es de mail
from email.mime.multipart import MIMEMultipart #Este es de mail
from datetime import datetime, time, timedelta 
from botocore.exceptions import NoCredentialsError


#############################################################################################################################################
#This corresponds to the banner that says something of detonaciones del chatbot
#Verified

st.set_page_config(page_title = "Pernexium", page_icon = "./Varios/Logo/PXM isotipo 2.png")

with open("./Varios/Logo/PXM Imagotipo 2.png", "rb") as image_file:
    encoded_image = base64.b64encode(image_file.read()).decode()
st.markdown(f"""
    <img src="data:image/png;base64,{encoded_image}" width="58%" height="270" style="display:block; margin-left:auto; margin-right:auto;" />
    """, unsafe_allow_html=True)

st.markdown("<h1 style='text-align: center;'>Detonaciones del  <span style='color: #145CB3;'>Chatbot</span></h1>", unsafe_allow_html=True)
st.markdown("<hr>", unsafe_allow_html=True)


#############################################################################################################################################
#Verified

def obtener_token_desde_secrets():
    ruta_secrets = ".streamlit/secrets.toml"
    secrets = toml.load(ruta_secrets)
    return secrets["tokens"]["TOKEN_PERNE"]


#############################################################################################################################################
#Verified

def seleccionar_bot_campana():
    url = "https://chatbot.pernexium.com.mx/prod/bots" 
    token_perne = obtener_token_desde_secrets()
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token_perne}" 
    }
    
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        if isinstance(data, list):
            options = []
            id_mapping = {}
            for item in data:
                option = f"{item['name']} - {item['id']}"
                options.append(option)
                id_mapping[option] = {
                    'id': item['id'],
                    'enterprise_id': item['enterprise_id']
                }
            if not options:
                options.append("No hay campañas disponibles")
        else:
            options = ["Datos inesperados recibidos"]
    else:
        options = ["Error al obtener campañas"]
    
    bot_name = st.selectbox("**1. CAMPAÑA Y BOT:**", options)
    st.markdown("<hr>", unsafe_allow_html=True)

    # Get the corresponding id and enterprise_id from the mapping
    bot_info = id_mapping.get(bot_name, {'id': 'Unknown ID', 'enterprise_id': 'Unknown Enterprise ID'})
    bot_id = bot_info['id']
    enterprise_id = bot_info['enterprise_id']
    
    return bot_id


#############################################################################################################################################
#Verified
#TODO implement this function in further dev, this actually retrieves the sessions, and let user select session
def seleccionar_session():
    url = "https://chatbot.pernexium.com.mx/prod/sessions"
    token_perne = obtener_token_desde_secrets()
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token_perne}" 
    }
    
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        if isinstance(data, list):
            options = []
            for item in data:
                option = item['id']
                options.append(option)
            if not options:
                options.append("No hay sesiones disponibles")
        else:
            options = ["Datos inesperados recibidos"]
    else:
        options = ["Error al obtener sesiones"]
    
    session_id = st.selectbox("**SESSION: **", options)
    st.markdown("<hr>", unsafe_allow_html=True)
    
    return session_id


#############################################################################################################################################
#Verified
#TODO ya no existe mora?
def seleccionar_contactacion():
    contact_type = st.selectbox("**2. TIPO DE CONTACTACIÓN:**", ["mora_agentes", "cosecha_y_conflicto_agentes"])
    
    # st.write("""
    # - **mora_agentes:** Mensajes de mora para agentes, se necesita subir la base de datos.
    # - **cosecha_y_conflicto_agentes:** Mensajes de cosecha y conflicto para agentes, se necesita subir la base de datos.
    # """)
    
    st.markdown("<hr>", unsafe_allow_html=True)
    return contact_type


#############################################################################################################################################
#Verified

def obtener_credenciales_aws():
    ruta_secrets = ".streamlit/secrets.toml"
    secrets = toml.load(ruta_secrets)
    aws_access_key_id = secrets["aws"]["aws_access_key_id"]
    aws_secret_access_key = secrets["aws"]["aws_secret_access_key"]
    return aws_access_key_id, aws_secret_access_key


#############################################################################################################################################


def subir_base(contact_type):

    if contact_type == "mora": #según entiendo esto ya no aparece
        return None, None
    
    aws_access_key_id, aws_secret_access_key = obtener_credenciales_aws()
    s3 = boto3.client('s3',aws_access_key_id=aws_access_key_id,aws_secret_access_key=aws_secret_access_key)
    
    st.write("**3. BASE DE DETONACIONES:**")
    st.write("*La base debe ser un archivo .xlsx y debe contener la columna 'credito'. El nombre de las columnas no debe contener carácteres especiales, esto incluye tildes y mayúsculas.*")
    uploaded_file = st.file_uploader("detonation base", type=["xlsx"], label_visibility="hidden") #Added non empty label to avoid errors
    #`label` got an empty value. This is discouraged for accessibility reasons and may be disallowed in the future by raising an exception. Please provide a non-empty label and hide it with label_visibility if needed.
    st.markdown("<hr>", unsafe_allow_html=True)
    
    data_base = None 
    
    if uploaded_file is not None:
        #bytes_data = uploaded_file.read()
        df = pd.read_excel(uploaded_file)
        df.columns = [unidecode(col).lower().replace(" ", "_") for col in df.columns]
        output = BytesIO()
        df.to_excel(output, index=False, engine='openpyxl')
        output.seek(0)
        
        hoy = datetime.now() - timedelta(hours=6) 
        year_month = hoy.strftime("%Y_%m")
        day_month = hoy.strftime("%m_%d")
        
        bucket_name = 's3-pernexium-report-2'
        folder_path = f"raw/bancoppel/detonaciones/{contact_type}/{year_month}/"
        
        if contact_type == "mora_agentes":
            file_name = f"base_mora_enviar_{day_month}.xlsx"
        elif contact_type == "cosecha_y_conflicto_agentes":
            file_name = f"base_cosechas_conflicto_enviar_{day_month}.xlsx"
        else:
            file_name = f"archivo_default_{day_month}.xlsx"  
        
        data_base = file_name
        s3_path = folder_path + file_name
        
        try:
            s3.put_object(Bucket=bucket_name, Key=s3_path, Body=output.getvalue())
            st.success(f"Archivo XLSX subido a S3 exitosamente.")
            st.markdown("<hr>", unsafe_allow_html=True)
        except NoCredentialsError:
            st.error("No se encontraron las credenciales de AWS.")
        except Exception as e:
            st.error(f"Error al subir el archivo: {e}")
    
    return uploaded_file, data_base

#Aqui se cambiaron varias cosillas, pero principalmente se añade pandas como una capa para verificar y sanitizar los datos del xlsx
#Creo que no afecta en nada, sospechaba que algo le dolía por unicode, pero no, creo que solo se usa aqui

#############################################################################################################################################
#Verified

def seleccionar_agentes():
    url = "https://chatbot.pernexium.com.mx/prod/agents"
    token_perne = obtener_token_desde_secrets()
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token_perne}" 
    }

    response = requests.get(url, headers=headers)

    def normalize_name(name):
        name = unidecode(name)
        name = name.replace('Ñ', 'N').replace('ñ', 'n')
        name = name.replace(' ', '_')
        name = name.upper()
        return name

    if response.status_code == 200:
        agentes = response.json()
        nombres_agentes = [normalize_name(agente['name']) for agente in agentes]
        emails_agentes = {normalize_name(agente['name']): agente['email'] for agente in agentes}  # Map names to emails
        ids_agentes = {normalize_name(agente['name']): agente['id'] for agente in agentes}
    else:
        st.error(f"Error al obtener los agentes: {response.status_code}")
        nombres_agentes = []
        emails_agentes = []
        ids_agentes = []

    if nombres_agentes:
        selected_agents = st.multiselect("**4. AGENTES:**", nombres_agentes)
        max_sends_per_day = st.number_input("**5. MÁXIMO DE ENVÍOS POR DÍA:**", min_value=0, step=100)
        max_messages_per_agent = st.number_input("**6. MÁXIMO DE MENSAJES POR AGENTE:**", min_value=0, step=100)
        st.markdown("<hr>", unsafe_allow_html=True)

        # Retrieve only the emails for selected agents
        selected_emails = [emails_agentes[agent] for agent in selected_agents]
        selected_ids = [ids_agentes[agent] for agent in selected_agents] #Add retrieving of agents id
        
        return selected_agents, max_sends_per_day, max_messages_per_agent, selected_emails, selected_ids
    else:
        st.error("No se pudieron obtener los agentes.")
        return [], 0, 0, [], []


#############################################################################################################################################
#DEPRECATED, NOW HANDLED BY THE BACK, CHECK IS NOT BEING USED IN CURRENT STREAMLIT

def enviar_email_ses(destinatarios, asunto, cuerpo_html):
    # Obtener las credenciales de AWS
    aws_access_key_id, aws_secret_access_key = obtener_credenciales_aws()

    # Crear un cliente de SES
    ses_client = boto3.client(
        'ses',
        region_name='us-east-2',
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key
    )

    # Configurar el correo electrónico
    remitente = 'enrique.ramirez@pernexium.com'  # Reemplaza con tu correo verificado en SES

    # Crear el objeto MIMEText
    mensaje = MIMEMultipart('alternative')
    mensaje['Subject'] = asunto
    mensaje['From'] = remitente
    mensaje['To'] = ', '.join(destinatarios)
    
    parte_html = MIMEText(cuerpo_html, 'html')
    mensaje.attach(parte_html)

    try:
        response = ses_client.send_raw_email(
            Source=remitente,
            Destinations=destinatarios,
            RawMessage={'Data': mensaje.as_string()},
        )
    except ClientError as e:
        print(f"Error al enviar el correo: {e.response['Error']['Message']}")
    else:
        print(f"Correo enviado. Message ID: {response['MessageId']}")


#############################################################################################################################################
#Verified, solo se añadio lo de guardar el output

def invocar_lambda_cosecha(selected_agents, max_sends_per_day, max_messages_per_agent):
    aws_access_key_id, aws_secret_access_key = obtener_credenciales_aws()
    
    client = boto3.client('lambda',aws_access_key_id=aws_access_key_id,aws_secret_access_key=aws_secret_access_key,region_name='us-east-2')
    
    payload = {
        'AGENTES': selected_agents,
        'max_filas_por_archivo': max_messages_per_agent,
        'max_envios_por_dia': max_sends_per_day
    }

    response = client.invoke(
        FunctionName='pernexium_analytics_bancoppel_detonaciones_chatbot_coco',  
        InvocationType='RequestResponse',
        Payload=json.dumps(payload)
    )
    print("cosecha_y_conflicto")
    
    output = json.loads(response['Payload'].read().decode('utf-8'))

    # Almacenar el output en session_state
    st.session_state.lambda_output = output

    return output


#############################################################################################################################################
#Verified, solo se añadio lo de guardar el output
#TODO remember check after definitive release, that in order of best practices, this returns the generated files, same for the lambda above

def invocar_lambda_mora(selected_agents, max_sends_per_day, max_messages_per_agent):
    aws_access_key_id, aws_secret_access_key = obtener_credenciales_aws()
    client = boto3.client('lambda',aws_access_key_id=aws_access_key_id,aws_secret_access_key=aws_secret_access_key,region_name='us-east-2')
    
    payload = {
        'AGENTES': selected_agents,
        'max_filas_por_archivo': max_messages_per_agent,
        'max_envios_por_dia': max_sends_per_day
    }

    response = client.invoke(
        FunctionName='pernexium_analytics_bancoppel_detonaciones_chatbot_moras',  
        InvocationType='RequestResponse',
        Payload=json.dumps(payload)
    )
    
    output = json.loads(response['Payload'].read().decode('utf-8'))

    # Almacenar el output en session_state
    st.session_state.lambda_output = output

    return output


#############################################################################################################################################
#Verified
#TODO here should receive also the session as a parameter so url is not fixed, but for demo keep it like this
def seleccionar_templates_por_agente(selected_agents):
    st.markdown("<hr>", unsafe_allow_html=True)
    url = "https://chatbot.pernexium.com.mx/prod/templates/session/353257377876857?session_id"
    token_perne = obtener_token_desde_secrets()
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token_perne}" 
    }

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        templates = response.json()
    else:
        st.error(f"Error al obtener los templates: {response.status_code}")
        return {}

    if not isinstance(templates, list) or not templates:
        st.error("No se encontraron templates en la respuesta o el formato es incorrecto.")
        return {}

    agent_templates = {}

    for agent in selected_agents:
        if f"{agent}_template" not in st.session_state:
            st.session_state[f"{agent}_template"] = random.choice(templates)

    for agent in selected_agents:
        random_template = st.session_state[f"{agent}_template"]
        template_names = [template['template_name'] for template in templates]
        
        selected_template_name = st.selectbox(
            f"**TEMPLATE PARA {agent}**:",
            template_names, 
            index=template_names.index(random_template['template_name']),
            key=f"{agent}_selectbox"  # Clave única, para evitar el error si se selecciona el mismo template
        )
        
        selected_template = next(template for template in templates if template['template_name'] == selected_template_name)
        template_content = selected_template.get('template', 'No template content')
        
        st.text_area(f"Contenido del template para {agent}:", template_content, height=150, key=f"{agent}_text_area")  # Lo mismo de arriba

        agent_templates[agent] = selected_template
        
    return agent_templates


#############################################################################################################################################
#Here the function only was updated so can support the correc timezone (mexico city)
#Verified, there should be no problem with this

def seleccionar_fecha_hora():
    mexico_tz = pytz.timezone('America/Mexico_City')
    current_date = datetime.now(mexico_tz)
    
    st.markdown("<hr>", unsafe_allow_html=True)
    
    selected_date = st.date_input(
        "**7. FECHA DE DETONACIÓN:**", 
        value=current_date.date(),
        min_value=current_date.date()
    )
    
    times = [time(hour, minute) for hour in range(24) for minute in range(0, 60, 10)]
    
    detonation_time = st.selectbox("**8. HORA DE DETONACIÓN:**", times, index=times.index(time(13, 0)))
    detonation_datetime = datetime.combine(selected_date, detonation_time)
    detonation_datetime = mexico_tz.localize(detonation_datetime) 
    
    if detonation_datetime <= current_date:
        st.error("La fecha y hora seleccionadas deben ser en el futuro.")
    else:
        st.info(f"Detonación programada para el día **{detonation_datetime.strftime('%d-%m-%Y')}** a las **{detonation_datetime.strftime('%H:%M:%S')}.**")
    
    st.markdown("<hr>", unsafe_allow_html=True)
    
    return detonation_datetime


#############################################################################################################################################
#Verified, actually the post method was not modified, the only thing that changed is the final message 

def enviar_detonacion(event_json):
    url = "https://gxtxk28bli.execute-api.us-east-2.amazonaws.com/prod/detonation/config"
    
    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(url, data=event_json, headers=headers)
        if response.status_code == 200:
            st.markdown("<hr>", unsafe_allow_html=True)
            st.success(f"Respuesta exitosa: {response.json()}")
        else:
            st.error(f"Error: {response.status_code}, {response.text}")
    except Exception as e:
        st.error(f"Error al enviar la detonación: {str(e)}")
    finally:
        #st.write("-----------------------------------------------------**DETONACIÓN FINALIZADA**-----------------------------------------------------")
        st.balloons()
        st.markdown("<hr>", unsafe_allow_html=True)

    st.markdown("""
        <div style="text-align: center;">
            <h4>¡Detonación finalizada, es hora de verificar!</h4>
            <p>Verifica con <a href="mailto:enrique.ramirez@pernexium.com">Enrique Ramírez</a> que los mensajes se hayan detonado a la hora que se estableció.</p>
        </div>
        """, unsafe_allow_html=True)
    st.markdown("<hr>", unsafe_allow_html=True)



#############################################################################################################################################


def generar_y_subir_json(contact_type, detonation_datetime, selected_agents, max_sends_per_day, max_messages_per_agent, agent_templates, bot_id, data_base, agent_mails, agent_ids, lambda_output):
    #TODO Debug remove
    #print(f"in generar y subir json, this is value of lambda_output: {lambda_output}") DEBUG, REMOVE
    #print(f"this after aplying str: {str(lambda_output)}") DEBUG, REMOVE
    mexico_tz = pytz.timezone('America/Mexico_City')
    current_date = datetime.now(mexico_tz)
    formatted_date = current_date.strftime('%Y_%m_%d')  
    year_month = current_date.strftime('%Y_%m')
    
    agent_templates_filtered = {}
    for agent, template_info in agent_templates.items():
        agent_templates_filtered[agent] = {
            "template_name": template_info.get("template_name")
        }

    generated_files = [f"{formatted_date}_{agent}.csv" for agent in agent_templates]#TODO pls correct with the propper name, could be returned by the lambda or even generated like this

    token = obtener_token_desde_secrets() #the token to be used in obtain wsbs

    event_data = {
        "bot_id": bot_id,
        "contact_type": contact_type,
        "data_base": data_base,
        "selected_agents": selected_agents,
        "agent_templates": agent_templates_filtered,
        "max_sends_per_day": int(max_sends_per_day),
        "max_messages_per_agent": int(max_messages_per_agent),
        "detonation_time": detonation_datetime.strftime('%d-%m-%Y %H:%M:%S'),
        "selected_session": "353257377876857", #Corresponds to the session (meta phone number)
        "generated_files": generated_files, #Corresponds to an array of the generated files in master
        "token": token, #corresponds to the token of cognito
        "agent_mails": agent_mails, # this corresponds to an array that contains the mails of selected agents
        "agent_ids": agent_ids,
        "lambda_output": str(lambda_output),
        "campaign": "bancoppel"
    }
    
    event_data_no_token = event_data.copy()
    event_data_no_token.pop("token", None)

    event_json_no_token = json.dumps(event_data_no_token, indent=4)

    event_data_final = {
        "bot_id": bot_id,
        "contact_type": contact_type,
        "data_base": data_base,
        "selected_agents": selected_agents,
        "agent_templates": agent_templates_filtered,
        "max_sends_per_day": int(max_sends_per_day),
        "max_messages_per_agent": int(max_messages_per_agent),
        "detonation_time": detonation_datetime.strftime('%d-%m-%Y %H:%M:%S'),
        "selected_session": "353257377876857", #Corresponds to the session (meta phone number)
        "generated_files": generated_files, #Corresponds to an array of the generated files in master
        "token": token, #corresponds to the token of cognito
        "agent_mails": agent_mails, # this corresponds to an array that contains the mails of selected agents
        "agent_ids": agent_ids,
        "lambda_output": str(lambda_output),
        "sanitized_json": str(event_json_no_token),
        "campaign": "bancoppel"
    }
    #TODO suggestion, not send again in json sanitizado the info of lambda_output, since in mail, that is the only part where is used, is not necessary

    event_json = json.dumps(event_data_final, indent=4)
    #st.code(event_json, language='json') 

    file_name = f"{formatted_date}_bancoppel_detonaciones_chatbot_{contact_type}_{year_month}.json"
    
    aws_access_key_id, aws_secret_access_key = obtener_credenciales_aws()
    s3 = boto3.client('s3',aws_access_key_id=aws_access_key_id,aws_secret_access_key=aws_secret_access_key)
    
    bucket_name = "s3-pernexium-report-2"
    s3_key = f"staging/bancoppel/detonaciones/{contact_type}/{year_month}/{file_name}" 

    try:
        s3.put_object(Bucket=bucket_name, Key=s3_key, Body=event_json_no_token) #upload without token
        #st.success(f"Archivo JSON subido a S3 exitosamente.")
    except Exception as e:
        st.error(f"Error al subir el archivo a S3: {str(e)}")

    return event_json


#############################################################################################################################################
#Verified

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


#############################################################################################################################################
#Verified

def login():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        #st.title("Iniciar Sesión")
        st.markdown("<h2 style='text-align: left;'>Iniciar Sesión</h2>", unsafe_allow_html=True)
        password = st.text_input("Contraseña", type="password")
        if st.button("Iniciar sesión"):
            if hash_password(password) == HASHED_PASSWORD:
                st.session_state.logged_in = True
                st.success("Has iniciado sesión correctamente.")
            else:
                st.error("Contraseña incorrecta.")
        return False
    else:
        return True


#############################################################################################################################################


HASHED_PASSWORD = st.secrets["hashed_password"]

def main():
    # Verifica si el usuario ha iniciado sesión
    if not login():
        return  # Si no ha iniciado sesión, no continuar

    # Aquí empieza el resto de tu aplicación
    if "configuracion_confirmada" not in st.session_state:
        st.session_state.configuracion_confirmada = False

    if "json_generado" not in st.session_state:
        st.session_state.json_generado = None

    if "csv_generado" not in st.session_state:
        st.session_state.csv_generado = False

    # Paso 0: Selecciona bot y campaña
    bot_id = seleccionar_bot_campana()

    # Paso 1: Selecciona tipo de contactación y subir base
    contact_type = seleccionar_contactacion()
    uploaded_file, data_base = subir_base(contact_type)

    # Valida si se necesita subir un archivo o no
    if contact_type != "mora" and uploaded_file is None:
        st.error("Por favor, sube una base de datos antes de continuar.")
        return  # Termina la ejecución si no se ha subido un archivo

    # Paso 2: Selecciona agentes y máximos
    selected_agents, max_sends_per_day, max_messages_per_agent, emails_agentes, ids_agentes = seleccionar_agentes()
    print(emails_agentes)

    if st.button("Generar CSV's vía Lambda"):
        try:
            if contact_type == "mora_agentes":
                output = invocar_lambda_mora(selected_agents, max_sends_per_day, max_messages_per_agent)
            elif contact_type == "cosecha_y_conflicto_agentes":
                output = invocar_lambda_cosecha(selected_agents, max_sends_per_day, max_messages_per_agent)
            else:
                st.error("Tipo de contactación no válido para generar CSV's.")
                return
            st.success(f"Respuesta de Lambda: {output}")
            st.session_state.lambda_output = output #aqui me queda la duda, de porque si en las lambdas, asignamos el valor este al st.session_state.lambda_output, aqui lo volvemos a hacer
            #capaz podemos borrar del de invocar_lambda_mora y del de invocar_lambda_cosecha esa parte que hace esto
            st.session_state.csv_generado = True 
        except Exception as e:
            st.error(f"Error al invocar Lambda: {str(e)}")

    if not st.session_state.csv_generado:
        st.markdown("<hr>", unsafe_allow_html=True)
        st.error("Debes generar los CSV's usando Lambda antes de continuar.")
        return

    # Paso 3: Selecciona templates para cada agente
    agent_templates = seleccionar_templates_por_agente(selected_agents)

    # Paso 4: Selección de la hora de detonación
    detonation_time = seleccionar_fecha_hora()

    if st.button("Confirmar configuración") and not st.session_state.configuracion_confirmada:
        st.markdown("<hr>", unsafe_allow_html=True)

        #TODO DEBUG REMOVE
        #print(f"what is containing session state lambda output: {st.session_state.lambda_output}")

        # Generate JSON and store it in session_state
        st.session_state.json_generado = generar_y_subir_json(
            contact_type, detonation_time, selected_agents, max_sends_per_day, max_messages_per_agent, agent_templates, bot_id, data_base, emails_agentes, ids_agentes, st.session_state.lambda_output
        )

        #TODO DEBUG REMOVE
        #print(f"generated_json: {st.session_state.json_generado}")
        # Only create json_sanitizado if json_generado was successfully created
        #if st.session_state.json_generado:
        #    json_sanitizado = json.loads(st.session_state.json_generado)  # Load the JSON if it's in string format
         #   json_sanitizado.pop('token', None)  # Remove sensitive information like tokens
            
            # Update session state to mark configuration as confirmed
        st.session_state.configuracion_confirmada = True
        st.success("Configuración confirmada correctamente.")
        #else:
        #    st.error("Error: No se pudo generar el JSON correctamente.")

    
    if st.session_state.json_generado:
        st.code(st.session_state.json_generado, language='json')

    if st.session_state.configuracion_confirmada:
        st.markdown("<hr>", unsafe_allow_html=True)

        if st.button("ENVIAR DETONACIONES"):
            if st.session_state.json_generado is not None:
                enviar_detonacion(st.session_state.json_generado)
                
                #if isinstance(st.session_state.json_generado, str):
                #        json_generado = json.loads(st.session_state.json_generado)
                #else:
                #        json_generado = st.session_state.json_generado

                #enviar_detonacion(json_generado)
                #json_sanitizado = json_generado.copy()
                #json_sanitizado.pop('token', None) 
                
                #timezone = pytz.timezone("America/Mexico_City")
                #fecha_actual = datetime.now(timezone).strftime('%d-%m-%Y')

                #destinatarios = ['hibran.tapia@pernexium.com', 'enrique.ramirez@pernexium.com'] 
                #asunto = f'Detonador del Chatbot - Detonación Agendada Exitosamente - {fecha_actual}'

                #lambda_output = st.session_state.get('lambda_output', 'No se obtuvo output de Lambda.')

                #enviar_email_ses(destinatarios, asunto, cuerpo_html=cuerpo_html)
            else:
                st.error("No se ha generado el JSON correctamente.")


#############################################################################################################################################


if __name__ == "__main__":
    main()

#TODO in general, remove remaining commented code
