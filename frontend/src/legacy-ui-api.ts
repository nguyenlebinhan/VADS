import {
  ApiError,
  generateKnowledgeGraph,
  getKnowledgeGraph,
  listDocuments,
  listRegulatoryDocuments,
  queryDocumentRag,
  uploadDocument,
  type DocumentPublic,
  type KnowledgeGraph,
  type RegulatoryDocument,
} from "./api";

export interface LegacyDocument {
  id: string;
  name: string;
  date: string;
  month: string;
  year: number;
  type: string;
  status: DocumentPublic["status"];
}

export interface LegacyLaw {
  id: number;
  documentId: string;
  name: string;
  category: string;
  status: string;
  year: number;
  issuer: string;
  number: string;
}

export interface LegacyLawDetail {
  description: string;
  chapters: Array<{ title: string; summary: string }>;
  relatedIds: number[];
  keywords: string[];
}

export interface LegacyTreeNode {
  id: string;
  label: string;
  type: "root" | "chapter" | "article";
  summary: string;
  children?: LegacyTreeNode[];
}

export interface LegacyKnowledgeTerm {
  id: string;
  term: string;
  definition: string;
  source: string;
  category: string;
  highlightTerm: string;
}

export interface LegacyPortalData {
  documents: LegacyDocument[];
  laws: LegacyLaw[];
  lawDetails: Record<number, LegacyLawDetail>;
}

const vietnameseDate = new Intl.DateTimeFormat("vi-VN", {
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
});

function documentType(title: string): string {
  const normalized = title.trim().toLocaleLowerCase("vi");
  if (normalized.startsWith("nghị định")) return "Nghị định";
  if (normalized.startsWith("thông tư")) return "Thông tư";
  if (normalized.startsWith("quyết định")) return "Quyết định";
  if (normalized.startsWith("nghị quyết")) return "Nghị quyết";
  if (normalized.includes("luật")) return "Luật";
  return "Văn bản";
}

function mapDocument(document: DocumentPublic): LegacyDocument {
  const createdAt = new Date(document.created_at);
  return {
    id: document.id,
    name: document.title,
    date: vietnameseDate.format(createdAt),
    month: `Tháng ${createdAt.getMonth() + 1}`,
    year: createdAt.getFullYear(),
    type: documentType(document.title),
    status: document.status,
  };
}

function mapLaw(document: RegulatoryDocument, index: number): LegacyLaw {
  return {
    id: index + 1,
    documentId: document.documentId,
    name: document.title,
    category: document.domain || document.documentType,
    status: document.status === "ANALYZED" ? "Còn hiệu lực" : "Cần rà soát",
    year: Number(document.issuedDate.slice(0, 4)) || new Date(document.createdAt).getFullYear(),
    issuer: document.issuingAgency,
    number: document.documentNumber,
  };
}

function lawDetail(document: RegulatoryDocument): LegacyLawDetail {
  return {
    description: document.executiveSummary || "Chưa có bản tóm tắt cho văn bản này.",
    chapters: [
      {
        title: `${document.documentType} · Phiên bản ${document.versionNumber}`,
        summary: document.executiveSummary || `Văn bản thuộc lĩnh vực ${document.domain}.`,
      },
    ],
    relatedIds: [],
    keywords: [document.domain, document.documentType, ...document.applicableSubjects]
      .filter(Boolean),
  };
}

export async function loadLegacyPortalData(): Promise<LegacyPortalData> {
  const [documents, regulatoryDocuments] = await Promise.all([
    listDocuments(),
    listRegulatoryDocuments().catch(() => []),
  ]);
  const laws = regulatoryDocuments.map(mapLaw);
  return {
    documents: documents.map(mapDocument),
    laws,
    lawDetails: Object.fromEntries(
      regulatoryDocuments.map((document, index) => [index + 1, lawDetail(document)]),
    ),
  };
}

export async function uploadLegacyDocument(file: File): Promise<void> {
  await uploadDocument(file);
}

function termsFromGraph(graph: KnowledgeGraph, document: LegacyDocument): LegacyKnowledgeTerm[] {
  return graph.nodes.map(node => ({
    id: `${document.id}:${node.id}`,
    term: node.name,
    definition: node.canonicalName || String(node.properties.description ?? node.name),
    source: document.name,
    category: node.type.replaceAll("_", " "),
    highlightTerm: node.name,
  }));
}

export async function loadLegacyKnowledgeTerms(
  documents: LegacyDocument[],
): Promise<LegacyKnowledgeTerm[]> {
  const settled = await Promise.all(
    documents.map(async document => {
      try {
        return termsFromGraph(await getKnowledgeGraph(document.id), document);
      } catch (reason) {
        if (reason instanceof ApiError && reason.code === "KNOWLEDGE_GRAPH_NOT_FOUND") {
          return [];
        }
        throw reason;
      }
    }),
  );
  return settled.flat();
}
async function graphFor(documentId: string): Promise<KnowledgeGraph> {
  try {
    return await getKnowledgeGraph(documentId);
  } catch (reason) {
    if (!(reason instanceof ApiError) || reason.code !== "KNOWLEDGE_GRAPH_NOT_FOUND") {
      throw reason;
    }
  }
  const generated = await generateKnowledgeGraph(documentId, false);
  if (!generated.graph) {
    throw new Error(`Workflow ${generated.workflowId} chưa tạo được đồ thị tri thức.`);
  }
  return generated.graph;
}

export async function loadLegacyGraph(
  document: LegacyDocument,
): Promise<{ tree: LegacyTreeNode; terms: LegacyKnowledgeTerm[] }> {
  const graph = await graphFor(document.id);
  const outgoing = new Map<string, string[]>();
  for (const edge of graph.edges) {
    const target = graph.nodes.find(node => node.id === edge.targetNodeId);
    if (!target) continue;
    const values = outgoing.get(edge.sourceNodeId) ?? [];
    values.push(`${edge.type.replaceAll("_", " ")} → ${target.name}`);
    outgoing.set(edge.sourceNodeId, values);
  }
  const groups = new Map<string, typeof graph.nodes>();
  for (const node of graph.nodes) {
    const nodes = groups.get(node.type) ?? [];
    nodes.push(node);
    groups.set(node.type, nodes);
  }
  const tree: LegacyTreeNode = {
    id: graph.versionId,
    label: document.name,
    type: "root",
    summary: `Knowledge Graph phiên bản ${graph.version} gồm ${graph.nodes.length} thực thể và ${graph.edges.length} quan hệ.`,
    children: [...groups.entries()].map(([type, nodes]) => ({
      id: `group-${type}`,
      label: type.replaceAll("_", " "),
      type: "chapter",
      summary: `${nodes.length} thực thể thuộc nhóm ${type.replaceAll("_", " ")}.`,
      children: nodes.map(node => ({
        id: node.id,
        label: node.name,
        type: "article",
        summary: [
          node.canonicalName,
          ...Object.entries(node.properties).map(([key, value]) => `${key}: ${String(value)}`),
          ...(outgoing.get(node.id) ?? []),
        ].filter(Boolean).join("\n"),
      })),
    })),
  };
  const terms = termsFromGraph(graph, document);
  return { tree, terms };
}

export async function askLegacyDocument(documentId: string, question: string): Promise<string> {
  const result = await queryDocumentRag(question, [documentId]);
  const citations = result.sources.slice(0, 3).map(source => {
    const location = [source.article, source.clause].filter(Boolean).join(", ");
    return `${location || source.document_title}: “${source.quote}”`;
  });
  return [result.answer, ...citations].join("\n\n");
}
