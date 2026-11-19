-- Zipsa droplet: drop files/folders onto the app icon to zip them.
-- (Keep this file ASCII-only; all Korean text comes from zipsa.py.)
--
-- zipsa.py --app-notify prints "title<newline>body": on stdout when it succeeds,
-- on stderr with exit code 1 when it fails. This app shows the notification/alert itself,
-- so it carries the Zipsa icon instead of Script Editor's.

on runZipsa(args)
	set py to POSIX path of (path to resource "zipsa.py")
	try
		set out to do shell script "/usr/bin/python3 " & quoted form of py & " --app-notify" & args
		if out is not "" then
			set {t, b} to my splitMessage(out)
			display notification b with title t
		end if
	on error errMsg number errNum
		if errNum is 1 then
			set {t, b} to my splitMessage(errMsg)
			display alert t message b as critical
		else
			display alert "Zipsa" message errMsg as critical
		end if
	end try
end runZipsa

-- first line = title, the rest = body
on splitMessage(s)
	set ps to paragraphs of s
	if (count of ps) < 2 then return {s, ""}
	set saved to AppleScript's text item delimiters
	set AppleScript's text item delimiters to linefeed
	set b to (items 2 thru -1 of ps) as text
	set AppleScript's text item delimiters to saved
	return {item 1 of ps, b}
end splitMessage

on open theItems
	set args to ""
	repeat with f in theItems
		set args to args & " " & quoted form of (POSIX path of (contents of f))
	end repeat
	my runZipsa(args)
end open

-- Finder right-click menu (the Finder extension) sends zipsa-finder://compress?p=...&t=...
-- zipsa.py checks the token and zips the paths.
on open location theURL
	my runZipsa(" --open-url " & quoted form of theURL)
end open location

-- Double-click: about + version + update (all dialogs are shown by zipsa.py)
on run
	set py to POSIX path of (path to resource "zipsa.py")
	try
		do shell script "/usr/bin/python3 " & quoted form of py & " --app"
	on error errMsg number errNum
		if errNum is not 1 then display alert "Zipsa" message errMsg as critical
	end try
end run
