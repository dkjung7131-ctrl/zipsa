-- Zipsa droplet: drop files/folders onto the app icon to zip them.
-- (Keep this file ASCII-only; all Korean text comes from zipsa.py.)

on open theItems
	set py to POSIX path of (path to resource "zipsa.py")
	set cmd to "/usr/bin/python3 " & quoted form of py & " --notify"
	repeat with f in theItems
		set cmd to cmd & " " & quoted form of (POSIX path of (contents of f))
	end repeat
	try
		do shell script cmd
	on error errMsg number errNum
		-- exit code 1 = zipsa already showed its own alert
		if errNum is not 1 then display alert "Zipsa" message errMsg as critical
	end try
end open

-- Double-click: about + version + update (all dialogs are shown by zipsa.py)
on run
	set py to POSIX path of (path to resource "zipsa.py")
	try
		do shell script "/usr/bin/python3 " & quoted form of py & " --app"
	on error errMsg number errNum
		if errNum is not 1 then display alert "Zipsa" message errMsg as critical
	end try
end run
