// This runs inside the database specified by MONGO_INITDB_DATABASE
db.notes.insertMany([
  {
    title: "Welcome to the Digital Vault",
    content: "This entry automatically inserted by MONGO_INITDB_DATABASE environment variable. It will run only one time",
    tags: ["fastapi", "python3.14"],
    created_at: new Date()
  }
]);