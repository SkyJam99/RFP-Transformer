from db_backend import get_proposals, get_supabase_connection

# This is set up as a daily task in PythonAnywhere to keep the database running (DB will sleep after 1 week of inactivity)
get_proposals(get_supabase_connection())