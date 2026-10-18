"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");
const root = path.resolve(__dirname, "..");
const source = fs.readFileSync(path.join(root, "app/static/i18n.js"), "utf8");

function load(locale, saved, blocked = false) {
  const context = vm.createContext({
    navigator: { language: locale },
    localStorage: {
      getItem() {
        if (blocked) throw new Error("Storage disabled");
        return saved;
      },
      setItem(key, value) {
        if (blocked) throw new Error("Storage disabled");
        saved = value;
      },
    },
    document: {
      documentElement: {},
      querySelector: (selector) => selector.startsWith("meta") ? {} : null,
    },
  });
  vm.runInContext(source, context);
  return (expression) => vm.runInContext(expression, context);
}

const french = load("fr-CA", null);
assert.equal(french("language"), "fr");
assert.equal(french("document.documentElement.lang"), "fr");
assert.equal(french("formatNumber(1.5, 1)"), "1,5");
assert.equal(french("formatNumber(0.015)"), "0,015");
assert.equal(french('tr("__proto__")'), "__proto__");
assert.equal(french('tr("Help with {0}.", "User text {1} <tag>")'), "Aider à réaliser ces tâches : User text {1} <tag>.");
assert.equal(french('localizeError("Add Internal portal to your tools before using it in a workflow.")'), "Ajoutez Internal portal à vos outils avant de l’utiliser dans un processus.");
assert.match(french('validationMessage({type:"less_than_equal", ctx:{le:1000}, loc:["body","workflows",0,"frequency_count"]})'), /1.*1000/);
const english = load("fr-FR", "en");
assert.equal(english("language"), "en");
assert.equal(english("formatNumber(1.5, 1)"), "1.5");
assert.equal(english('tr("Unknown {0}", "answer")'), "Unknown answer");
assert.equal(load("en-US", "invalid")("language"), "en");
const blocked = load("fr-FR", null, true);
assert.equal(blocked("language"), "fr");
blocked('setLanguage("en")');
assert.equal(blocked("document.documentElement.lang"), "en");

const catalog = JSON.parse(french("JSON.stringify(french)"));
const placeholders = (value) => (value.match(/\{\d+\}/g) || []).sort();
for (const [key, value] of Object.entries(catalog)) {
  assert.deepEqual(placeholders(value), placeholders(key), `Placeholders: ${key}`);
}
for (const file of ["app.js", "i18n.js"]) {
  const code = fs.readFileSync(path.join(root, "app/static", file), "utf8");
  for (const match of code.matchAll(/\btr\(("(?:[^"\\]|\\.)*")/g)) {
    const key = JSON.parse(match[1]);
    assert.ok(Object.hasOwn(catalog, key), `Missing French translation: ${key}`);
  }
}
console.log(`Localization checks passed (${Object.keys(catalog).length} translations).`);
