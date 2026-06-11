const assert = require('assert');
const fs = require('fs');
const path = require('path');

const localesRoot = path.resolve(__dirname, '../../src/extension/public/_locales');
const requiredLocales = ['zh', 'en', 'ja', 'es'];
const requiredKeys = [
  'extName',
  'extDescription',
  'unsupportedPage',
  'unreadableSite',
  'extractContentFailed',
  'enterReadingSessionFailed',
  'immersiveReadingLabel',
  'generateQuestionsTooltip',
  'exitReadingModeTooltip',
  'questionsLabel',
  'noQuestionsGenerated',
  'generatingQuestions',
  'failedToGenerateQuestions',
  'extensionMessagingUnavailable',
  'pageContentTooShort',
];

for (const locale of requiredLocales) {
  const filePath = path.join(localesRoot, locale, 'messages.json');
  assert(fs.existsSync(filePath), `${locale} locale should exist`);

  const messages = JSON.parse(fs.readFileSync(filePath, 'utf-8'));
  for (const key of requiredKeys) {
    assert(messages[key], `${locale} locale should define ${key}`);
    assert(
      typeof messages[key].message === 'string' && messages[key].message.trim().length > 0,
      `${locale}.${key} should contain message text`,
    );
  }
}

console.log('Extension locale resource checks passed');
