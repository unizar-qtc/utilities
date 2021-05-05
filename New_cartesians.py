#!/usr/bin/python3

from sys import argv

nombre_archivo = argv[1]

if nombre_archivo == "-h" or "help" in nombre_archivo:
    print("El programa lee un .log que haya acabado por tener un angulo de 180º y lo mueve ligeramente y genera un nuevo .gjf")
    print(">>   New_cartesians.py archivo.log     ")
    quit()

elif nombre_archivo[-3:] != "log":
    print("Se esperaba un archivo.log")
    quit()


with open(nombre_archivo, "r+") as contenidos_archivo:
    num_linea = 0
    lectura_keywords = "closed"
    lectura_ModRedundant = "closed"

    for linea in contenidos_archivo:
        num_linea += 1

        if " Center     Atomic      Atomic             Coordinates (Angstroms)" in linea: #Tomamos esta referencia para encontrar las geometrias
            linea_geometrias = num_linea

        elif "Bend failed for angle" in linea:
            atomo_a_mover = int(linea.split(' ')[-1]) - 1

        elif "Multiplicity" in linea:
            Carga = linea[10:12]
            Multiplicidad = linea[28:30]


        elif "Link 1" in linea:  # El Link 1 indica el principio del archivo, asi que limpiamos las especificaciones y Modredundant que pudiesemos tener del anterior
            Especificaciones = []
            ModRedundant_Coordinates=[]

        elif "%" in linea:                  #Todas las especificaciones para la maquina comienzan con % como 2 caracter
            Especificaciones.append(linea)  #Se guardan las especificaciones para generar el nuevo archivo con las mismas
            
            lectura_keywords = "open"       #Se abre la posibilidad de que lea los siguientes keywords que encuentre
            keywords = ""                   #Si fuese la segunda que se leen keywords se borran los anteriores


        elif "-----------" in linea and lectura_keywords == "open":   # pasado el %chk y demas los keywords estan enmarcados por ---
            lectura_keywords = "reading"

        elif "-----------" in linea and lectura_keywords == "reading": # cuando llega a la segunda linea se acabaron las keywords
            lectura_keywords = "closed"                                # por motivos obvios debe ir por delante de la parte que hace el append

        elif lectura_keywords == "reading":
            keywords += str(linea.rstrip("\n ")[1:])  # eliminamos el salto de linea y el espacio


        elif "The following ModRedundant input section has been read:" in linea:
            lectura_ModRedundant = "open"

        elif lectura_ModRedundant == "open" and "GradGradGrad" in linea:
            lectura_ModRedundant = "closed"

        elif lectura_ModRedundant == "open":
            ModRedundant_Coordinates.append(linea)



    linea_geometrias += 2 #De la cabecera al primer atomo hay 3 lineas

    lista_atomos = []
    lista_xyz = []

    num_linea = 0
    contenidos_archivo.seek(0) # volvemos a la primera fila del .log

    for linea in contenidos_archivo:
        num_linea += 1

        if "---------" not in linea and num_linea > linea_geometrias:
            lista_atomos.append(int(linea[14:20]))

            x = float(linea[37:48])
            y = float(linea[49:60])
            z = float(linea[61:71])
            lista_xyz.append([x,y,z])
            

        elif "---------" in linea and num_linea > linea_geometrias:
            break


    # Movemos uno de los atomos que esta a 180º
    for coord in range(len(lista_xyz[atomo_a_mover])):
        lista_xyz[atomo_a_mover][coord] = 0.01 + float(lista_xyz[atomo_a_mover][coord])

    # elimizanos el geom=check para no chafarnos las nuevas geometrias
    if "geom=check" in keywords:
        keywords = keywords.replace("geom=check", "")

#Una vez ya tenemos todo lo que nos interesa del .log podemos generar el nuevo input
with open(nombre_archivo[:-4]+"_r.gjf", "+w") as nuevo_input:

    for elemento in Especificaciones:
        nuevo_input.write(elemento)

    nuevo_input.write(keywords)
    nuevo_input.write('\n\n')

    nuevo_input.write("Generado con New_cartesians.py")
    nuevo_input.write('\n\n')

    nuevo_input.write(Carga+" "+Multiplicidad)

    for num_atomo in range(len(lista_atomos)):
        nuevo_input.write(" "+str(lista_atomos[num_atomo])+"   ")
        nuevo_input.write(str(lista_xyz[num_atomo][0])+"  "+str(lista_xyz[num_atomo][1])+"  "+str(lista_xyz[num_atomo][2])+"\n")

    nuevo_input.write('\n')

    for elemento in ModRedundant_Coordinates:  #Si esta vacio no pasa nada
        nuevo_input.write(elemento)

    nuevo_input.write("\n")

    
print(nombre_archivo[:-4]+"_r.gjf generado")



