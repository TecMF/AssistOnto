import chromadb
from pathlib import Path

def go_doc_db(docdb_path, doc_dir, queries, reset_db):
    """Build document DB from plaintext documents in doc_dir, optionally querying them."""
    client = chromadb.PersistentClient(path=docdb_path)
    if reset_db:
        client.reset()
        return
    collection = client.get_or_create_collection(name="assistonto_docs")
    if doc_dir:
        docdir_path = Path(doc_dir)
        if not docdir_path.is_dir():
            raise Exception(f"Expected a directory path, got {doc_dir}")
        doc_paths = [p for p in docdir_path.iterdir() if p.is_file()]
        doc_ids = [p.stem for p in doc_paths]
        docs = [p.read_text() for p in doc_paths]
        collection.add(
            documents=docs,
            ids=doc_ids,
        )
    if queries:
        results = collection.query(
            query_texts=queries,
            n_results=2,
            include=['documents'],
        )
        print(results)

def query_doc_db(docdb_path, query_txts, n_results=3):
  rag_client = chromadb.PersistentClient(path=docdb_path)
  collection = rag_client.get_or_create_collection(name="assistonto_docs")
  related_docs = collection.query(
    query_texts=query_txts,
    n_results=n_results,
    include=['documents'],
  )
  return related_docs['documents']
