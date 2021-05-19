#!/bin/bash

#################################################################################################################################################
#################################################################################################################################################
##                                                                                                                                             ##          
## Este programa esta pensado para ser añadido en el crontab y que se ejecute constantemente por su cuenta, para ello ejecuta:                 ##     
##           $ crontab -e                                                                                                                      ##     
##                                                                                                                                             ##         
## para ejecutar el programa cada 10 min pon:                                                                                                  ##   
##           */10 * * * * /bin/Seguimiento.sh                                                                                                  ##           
##                                                                                                                                             ##    
##                                                                                                                                             ##    
## Tambien será necesario añadir un apartado en los lanzadores que añada información de los calculos lanzados a calculos_lanzados.txt          ##      
## echo "$archivo_output $ID_calculo $date" >> calculos_lanzados.txt                                                                           ##        
##                                                                                                                                             ##        
## Un ejemplo para un calculo de gaussian:                                                                                                     ##      
## sleep 0.5                                                   #dejamos tiempo para que el calculo aparezca en el qstat                        ##
##                                                                                                                                             ##
## #incluimos el archivo con su ID en la lista de seguimiento                                                                                  ##
## /cm/shared/apps/sge/6.2u5p2/bin/lx26-amd64/qstat > IDs.job  # creamos un archivo temporal con el qstat                                      ##
## id_num=`tail -n 1 IDs.job | cut -c1-7 `                     # tomamos los 7 primeros caracteres que son el ID del calculo                   ##
## fecha=$(date +"%T %d-%m") `                                 # fecha y hora a la que el calculo es lanzado/entra                             ##
## archivo=$id_num'    '$donde/$calc.log'     '$fecha          # esto es lo que se añadira a calculos lanzados                                 ##
##                                                                                                                                             ##
## echo "$archivo" >> $HOME/bin/calculos_lanzados.txt                                                                                          ##
## rm IDs.job                                                                                                                                  ##     
##                                                                                                                                             ##     
## Aparte recominedo añadir al .bashrc:                                                                                                        ##     
##          echo "--CALCULOS CORRIENDO--"                                                                                                      ##     
##          cat calculos_corriendo.txt                                                                                                         ##     
##          echo " "                                                                                                                           ##     
##          echo "--CALCULOS TERMINADOS--"                                                                                                     ##     
##          cat calculos_terminados.txt                                                                                                        ##     
##          echo " "                                                                                                                           ##     
##                                                                                                                                             ##     
##                                                                                                                                             ##     
#################################################################################################################################################
#################################################################################################################################################

# variables de ficheros para uso interno del programa
fichero_calculos_lanzados="$HOME/bin/calculos_lanzados.txt"
fichero_calculos_corriendo="$HOME/bin/calculos_corriendo.txt"
fichero_calculos_terminados="$HOME/bin/calculos_terminados.txt"

# empezamos por crear una lista de los calculos que vamos a comprobar el estado y otra paralela con su ID
declare -a calculos_por_mirar #seran arrays
declare -a nums_ID_por_mirar
declare -a fecha_lanzamiento  #date +"%T %d-%m"

# Comprobamos que el fichero con los calculos lanzados existe y que no está vacío
if [ ! -s ${fichero_calculos_lanzados} ] || [[ -z $(grep '[^[:space:]]' ${fichero_calculos_lanzados}) ]]; then 
   exit 1
fi

# Llenaremos las listas con el contenido de calculos_lanzados.txt
nums_ID_por_mirar=( $(awk '{print $1}' ${fichero_calculos_lanzados}) )                        # el ID del calculo va en la primera columna
calculos_por_mirar=( $(awk '{print $2}' ${fichero_calculos_lanzados}) )                       # el nombre del calculo va en la segunda columna
fecha_lanzamiento=( $(awk '{printf("%s_%s\n"), $3, $4}' ${fichero_calculos_lanzados}) )       # la fechas son los 2 siguientes huecos (separamos por barrabaja)

# guardamos en una variable la salida del sistema de colas (contiene los IDs nuestros calculos)
# cross-compatibility: iterar y acumular la salida de los programas de MEMENTO/CIERZO/...
job_reporters=('/cm/shared/apps/sge/6.2u5p2/bin/lx26-amd64/qstat' '/cm/shared/apps/slurm/14.11.6/bin/sacct')
for reporter in ${job_reporters[@]}; do { queue_report+=$($reporter) ; } 2>/dev/null ; done

rm ${fichero_calculos_corriendo} 2>/dev/null # eliminamos calculos_corriendo porque ahora volveremos a examinar su estado y reescribirlo 

# Entramos en cada uno de los archivos y comprobamos su estado
# para iterar en el ciclo emplearemos el indice (!) en array de los calculos por mirar en lugar de los nombres

for indice in "${!calculos_por_mirar[@]}" 

do   # Se contrastan los calculos que hay que mirar con cada uno que sigue corriendo

    Calculo_abreviado=$( echo ${calculos_por_mirar[$indice]} | cut -d/ -f 4-99 )
    
    # Output por defecto
    Tarea="       UNKNOWN"
    Estado=" "
    Ciclos=" " 
 
    if [[ "${queue_report}" =~ "${nums_ID_por_mirar[$indice]}" ]]
    then # Si lo encuentra entre los IDs, el calculo todavia no ha acabado y veremos en que estado esta 
        
        # Comprobamos si ya existe un output, si no es posible que este esperando en cola
        if [[ -f "${calculos_por_mirar[$indice]}" ]] 
        then
            #                                                                           # 
            #-----------------------------CALCULO CORRIENDO-----------------------------#
            #                                                                           #

            # Queremos reconocer el programa que esta corriendo, 
            # para ello tenedremos que encontrar un fragmento de texto identificativo 
            # en el archivo que hemos puesto como calculo lanzado
            
            if grep -q  "Gaussian, Inc" ${calculos_por_mirar[$indice]}
            then    
                #############################################
                #              --   GAUSSIAN  --            #
                #############################################

                # Lo primero será ver que tarea esta realizando

                # leemos la ultima linea que tenga un # que contendra las keywords del job que le hemos pedido
                # Por si acaso cojo las 2 siguientes ñineas, por tener en cuenta lo largo que puede ser 
                # elimino los simbolos de salto de linea y espacios por evitarme posibles problemas de formateo
                Linea_de_keywords=$( grep "#" -A 2 ${calculos_por_mirar[$indice]} | tail -n 3 | tr -d '\n' | tr -d '[:space:]' )
                Linea_de_keywords=${Linea_de_keywords,,} #para evitar problemas con las mayusculas lo hacemos todo minusculas

                if grep -q "scan" ${calculos_por_mirar[$indice]}; then # comprobamos si es un scan

                    Tarea="SCAN"
                    # Miramos la linea de scan point para ver la cantidad de puintos del scan que ha avanzado
                    Estado=$( grep "scan point" ${calculos_por_mirar[$indice]} | tail -n 1 | awk '{print $(NF-3),"/",$(NF)}' | tr -d " " )
                    
                    Ciclos=$( grep "scan point" ${calculos_por_mirar[$indice]} | tail -n 1 | awk '{print $3}' | tr -d " " )
                                        L_ciclos=$( expr 3 - ${#Ciclos} )
                                        for ((i=0; i<${L_ciclos}; i++)){ Ciclos=' '$Ciclos; }
                    Ciclos="${Ciclos} cic"
                    
                elif grep -q "IRC-IRC" ${calculos_por_mirar[$indice]}; then # es un IRC

                    Tarea="IRC "
                    # Miramos la linea de scan point para ver la cantidad de puintos del scan que ha avanzado
                    Estado=$( grep " Pt " ${calculos_por_mirar[$indice]} | tail -n 1 | awk '{print $2}' | tr -d " " )
                    Estado+="$( grep "Maximum points per path" ${calculos_por_mirar[$indice]} | tail -n 1 | awk '{print "/",$(NF)}' | tr -d " " )"
                    
                    Ciclos=$( grep "Pt" ${calculos_por_mirar[$indice]} | tail -n 1 | awk '{print $2}' | tr -d " " )
                                        L_ciclos=$( expr 3 - ${#Ciclos} )
                                        for ((i=0; i<${L_ciclos}; i++)){ Ciclos=' '$Ciclos; }
                    Ciclos="${Ciclos} cic"
                    
                elif [[ -z "${Linea_de_keywords##*'ts'*}"  ]]; then # si es un ts	
                       
                    Tarea=" TS "
                    # Buscamos el ultimo Link 1 para solo tener en cuenta el avance desde que se lanza la actual parte del calculo

                    Linea_Link1=$( grep -n "Link 1" ${calculos_por_mirar[$indice]} | tail -n 1 | awk -F: '{print $1}' )
                    # A partir de esa linea miramos la convergencia
                        Estado=$( tail -n +${Linea_Link1} ${calculos_por_mirar[$indice]} | grep -A 4 "Converged?" | tail -n 4 | grep "YES" | wc -l )
                    Estado=" ${Estado}/4 "

                    Ciclos=$( tail -n +${Linea_Link1} ${calculos_por_mirar[$indice]} | grep "Converged?" | wc -l)
                                        L_ciclos=$( expr 3 - ${#Ciclos} )
                                        for ((i=0; i<${L_ciclos}; i++)){ Ciclos=' '$Ciclos; }
                    Ciclos="${Ciclos} cic"
                    
                elif [[ -z "${Linea_de_keywords##*'opt'*}"  ]]; then # si es una optimizacion a minimo
                       
                    Tarea="OPT "

                    Linea_Link1=$( grep -n "Link 1" ${calculos_por_mirar[$indice]} | tail -n 1 | awk -F: '{print $1}' )
                    Estado=$( tail -n +${Linea_Link1} ${calculos_por_mirar[$indice]} | grep -A 4 "Converged?" | tail -n 4 | grep "YES" | wc -l )
                    Estado=" ${Estado}/4 "

                    Ciclos=$( tail -n +${Linea_Link1} ${calculos_por_mirar[$indice]} | grep "Converged?" | wc -l )
                                        L_ciclos=$( expr 3 - ${#Ciclos} )
                                        for ((i=0; i<${L_ciclos}; i++)){ Ciclos=' '$Ciclos; }
                    Ciclos="${Ciclos} cic"

                elif [[ -z "${Linea_de_keywords##*'freq'*}"  ]]; then # si es un calculo de frequencias
                    Tarea="FREQ"
                else # será un calculo puntual
                    Tarea="SCF "
                fi

            elif grep -Fq  "GROMACS" ${calculos_por_mirar[$indice]}
            then 
                #############################################
                #              --   GROMACS  --             #
                #############################################

                Tarea=" MD "

                Limite_ciclos=$( grep "nsteps" ${calculos_por_mirar[$indice]} | awk '{print $3}' )
                Estado=""
                Ciclos=$( grep -A 1 " Step           Time" ${calculos_por_mirar[$indice]} | awk '{print $1}' | tail -n 1 )
                Ciclos="$Ciclos/$Limite_ciclos steps"
            elif grep -q  "DYNAMO Module Library" ${calculos_por_mirar[$indice]}
            then
                Tarea=$(awk '/>>> / {print $2 }' ${calculos_por_mirar[$indice]})
            fi
        else
            ######## SI EL OUTPUT NO SE HA GENERADO TODAVIA ENTONCES DEBE ESTAR ESPERANDO EN COLA #########
            Tarea=""
            Estado="WAITING IN QUEUE"
        fi

        # finalmente preparamos el mensaje que pondremos en calculos corriendo 
        IFS='' #Cambiamos el Internal Field Separator para que no se coma los espacios que ponemos en la linea de Output

        Output="  ${nums_ID_por_mirar[$indice]}  ||  "
        Output+="${Tarea} ${Estado} ${Ciclos}   ${Calculo_abreviado}"

        Resto=$( expr 120 - ${#Output} )
        for ((i=0; i<${Resto}; i++)){ Output+=' '�; }    #Añadimos espacios hastllegar 120 caracteres

        Output+="  ||   lanzado $(echo ${fecha_lanzamiento_1[$i]} | tr '_' ' ' )"   # Sustimos barrabaja por espacio
        
        echo $Output >> ${fichero_calculos_corriendo}

    else # Si no lo encuentra el ID  es porque el calculo ha acabado

        #                                                                           # 
        #-----------------------------CALCULO ACABADOS------------------------------#
        #                                                                           #

        if [[ -f "${calculos_por_mirar[$indice]}" ]]; then # Por si acaso comprobamos si el calculo existe
            # Si sabemos que existe tenemos que comprobar el programa que es
            # GAUSSIAN
            if grep -q  "Gaussian, Inc" ${calculos_por_mirar[$indice]}; then
                if ( tail -n 1 ${calculos_por_mirar[$indice]} | grep -q "Normal termination" ); then 
                    Tarea="          DONE"
                else
                    Tarea="          FAIL"
                fi
            # GROMACS
            elif grep -q  "GROMACS" ${calculos_por_mirar[$indice]}; then
                if grep -q "Normal termination" $( tail -n 1 ${calculos_por_mirar[$indice]} ); then 
                    Tarea="          DONE"
                else
                    Tarea="          FAIL"
                fi
            # DYNAMON
            elif grep -q  "DYNAMO Module Library" ${calculos_por_mirar[$indice]}; then
                if grep -q "<<<<<<<<<<<<" $( tail -n 1 ${calculos_por_mirar[$indice]} ); then 
                    Tarea="          DONE"
                else
                    Tarea="          FAIL"
                fi
            fi
        else
            Tarea="         ERROR"
        fi

        IFS='' #Cambiamos el Internal Field Separator para que no se coma los espacios que ponemos en la linea de Output

        Output="   ${Tarea}  ${Estado}  ${Ciclos}    ${Calculo_abreviado}"
        Resto=$( expr 120 - ${#Output} )
        for ((i=0; i<${Resto}; i++)){ Output+=' '�; }    #Añadimos espacios hastllegar a2110 caracteres
        
        fecha_terminacion=$( date +"%T %d-%m" )
        Output+="  || terminado ${fecha_terminacion}"
        echo $Output >> ${fichero_calculos_terminados}

        resto_de_calculos=$( grep -v ${calculos_por_mirar[$indice]} ${fichero_calculos_lanzados} )
        echo $resto_de_calculos > ${fichero_calculos_lanzados} 

    fi

done




