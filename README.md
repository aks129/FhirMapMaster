

# 🕸️ Parker: The FHIR Mapper & Converter Tool

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://fhirmapmaster.streamlit.app)
[![GitHub](https://img.shields.io/badge/GitHub-View%20on%20GitHub-blue)](https://github.com/aks129/FhirMapMaster)
[![Deploy](https://img.shields.io/badge/Deploy-On%20Streamlit-red)](https://share.streamlit.io/deploy?repository=https://github.com/aks129/FhirMapMaster)

**Parker** is an intelligent, flexible FHIR mapping tool that enables users to transform healthcare data from legacy and flat file formats (CSV, HL7 v2, CCDA, JSON, XML) into clean, standards-compliant **FHIR resources**. Choose your destination spec — such as **US Core**, **CARIN Blue Button**, or **Da Vinci PDex** — and Parker guides you through the mapping, validation, and transformation process.

## 🚀 Live Demo

**Try Parker now:** [https://fhirmapmaster.streamlit.app](https://fhirmapmaster.streamlit.app)

> ⚠️ **IMPORTANT**: This is experimental software for proof of concept only. Do NOT load PHI or confidential data.

---

## 🧭 Why Parker?

Healthcare data is messy, siloed, and non-standard. Parker solves this by:

* Supporting multiple **input data types** (CSV, HL7 v2, CCDA, JSON, etc.)
* Letting users **select target FHIR IGs** (US Core, CARIN BB, QI-Core, etc.)
* Guiding mapping with **smart suggestions** and **auto-alignment**
* Producing **valid, structured FHIR bundles** ready for APIs, analytics, or storage
* Supporting **manual override + visual UI** for precision

---

## 💡 Key Features

| Feature                    | Description                                                 |
| -------------------------- | ----------------------------------------------------------- |
| 🧾 Multi-format Input      | Import HL7 v2, CCDA, CSV, JSON, or XML                      |
| 📚 IG-based Mapping        | Map to US Core, CARIN BB, Da Vinci, and others              |
| 🧠 AI-Assisted Mapping     | Suggests FHIR elements for non-obvious fields               |
| 🛠 Visual UI + CLI Support | Use the UI for interactive mapping, or batch via CLI        |
| ✅ Validation Engine        | Validates output against StructureDefinitions and ValueSets |
| 📦 Export Options          | FHIR Bundle, NDJSON, or per-resource export                 |

---

## 📂 Input Formats Supported

* ✅ CSV (flat file EHR exports or registry data)
* ✅ HL7 v2 (ADT, ORU, VXU, etc.)
* ✅ CCDA (Continuity of Care Documents)
* ✅ JSON/XML (Custom or standard EMR formats)
* 🧪 EDI 837 (beta)

---

## 🎯 Output Targets

* HL7 **FHIR R4** (R5 roadmap)
* Implementation Guides:

  * **US Core 6.1.0+**
  * **CARIN Blue Button**
  * **Da Vinci PDex**
  * **QI-Core**
  * **Custom IGs (via StructureDefinition upload)**

---

## ⚙️ How It Works

1. **Upload Source File** (CSV, HL7 v2, etc.)
2. **Select Destination IG/Profile**
3. **Map Fields** with:

   * Auto-mapped suggestions
   * Manual overrides
   * Drop-downs for CodeSystems, ValueSets
4. **Validate** against FHIR spec and selected IG
5. **Export** as Bundle or individual FHIR resources

---

## 🚀 Quick Start

### CLI

```bash
npx parker-fhir-cli --input data.csv --ig uscore --profile Patient
```

### Web UI

1. Launch app with `npm run start` or Docker
2. Upload file
3. Select mapping
4. Download FHIR Bundle or send via API

---

## 📦 Installation

```bash
git clone https://github.com/your-org/parker-fhir-mapper.git
cd parker-fhir-mapper
npm install
npm start
```

Or with Docker:

```bash
docker build -t parker .
docker run -p 3000:3000 parker
```

---

## 🧪 Example Use Case

Input CSV:

```csv
id,first_name,last_name,dob,sex
12345,John,Doe,1980-03-15,M
```

Mapped FHIR Output:

```json
{
  "resourceType": "Patient",
  "id": "12345",
  "name": [{ "given": ["John"], "family": "Doe" }],
  "gender": "male",
  "birthDate": "1980-03-15"
}
```

---

## 🧭 Roadmap

* [ ] Auto-code lookup for LOINC/SNOMED bindings
* [ ] Bulk ingest + parallel mapping
* [ ] Integrated MCP model prompt builder
* [ ] Reconciliation with existing FHIR endpoints (de-duplication)
* [ ] Support for AI agent-generated mapping templates

---

## 🤝 Contributing

We welcome community feedback and contributions! Open an issue or submit a pull request to help improve the mapper or add support for new formats and IGs.

---

## 👤 Maintainer

Built by **FHIR IQ / Eugene Vestel**
🌐 [https://www.fhiriq.com](https://www.fhiriq.com)
📣 Join the [FHIR Goats LinkedIn Group](https://www.linkedin.com/groups/12732939/)

---

## 📜 License

Apache 2.0 — open-source and made for real-world FHIR implementers.
