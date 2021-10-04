### TinyOlap Sample Data Model
#Tutor
### Purpose of Data Model
The **tutor** data model is a typical **sales planning and reporting** data model.
Although being very old and special (see *History* below) it nicely reflects how 
business often was and still is structured. 

### Contents of Data Model
It contains products (PRODUKTE), regions (REGIONEN), time dimensions (JAHRE, MONATE), 
some value types (DATENART) with actual ('Ist') and plan figures, and finally a small 
set of measures (WERTART) contain quantity ('Menge'), sales ('Umsatz'), cost 
('variable Kosten') and a profit contribution ('DB1').

Tutor is the largest sample data model coming with TinyOlap. With exactly **135,443 
records**, it's already reflects a somehow realistic data volume for the business 
planning of a smaller to mid-sized company. Enjoy this ...

### History - a vintage-style sample
The **tutor** data model is a piece of OLAP history, it's almost 30 years old - from 
the pre-internet area. It's in german language, but should be understandable for everyone.
The TXT files in folder *tutor* are the original files ship with the database on a 
3½-inch disk at around 1995, they are **latin-1** encoded (ISO 8859-1).

The Tutor data model was shipped as the sample database of **MIS Alea**, one of the 
first *true* MOLAP databases available. MIS Alea was developed by the MIS Group in 
Darmstadt, Germany. Actutally MIS Alea was a clone of TM/1, which itself was developed 
by [Manny Perez](https://cubewise.com/history/) at Sinper Corp., USA. After several 
company transitions, MIS Alea is still successful in the BI market and is now owned 
by Infor and currently called **Infor d/EPM v12**, if I'm not mistaken.

