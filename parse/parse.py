with open('tracks_per_year.txt','r') as in_file:
    with open('musicinput.sql','w') as out_file:
        print >> out_file, "SET ESCAPE \'\\\'"
        for x in in_file:
            SQL_in = x.rstrip() #Get rid of those newlines
            SQL_out = 'INSERT INTO Music VALUES('
            SQL_vals = SQL_in.split('<SEP>')
            # Grab vals from split
            year    = SQL_vals[0].replace('\'', '\'\'').replace('\"', '\"\"').replace('&', '\\&')
            song_ID = SQL_vals[1].replace('\'', '\'\'').replace('\"', '\"\"').replace('\&', '\\&')
            artist  = SQL_vals[2].replace('\'', '\'\'').replace('\"', '\"\"').replace('\&', '\\&')
            song    = SQL_vals[3].replace('\'', '\'\'').replace('\"', '\"\"').replace('\&', '\\&')
            SQL_out += ('\'' + artist + '\'' + ',' + '\'' + song_ID + 
                        '\'' + ',' + '\'' + song + '\'' + ','  + year + ');')
            print >> out_file, SQL_out
