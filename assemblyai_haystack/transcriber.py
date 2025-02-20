from typing import Dict, List, Any, Optional
from pathlib import Path

from enum import Enum

from canals.serialization import default_to_dict, default_from_dict
from haystack.preview import component, Document

import assemblyai as aai

@component
class AssemblyAITranscriber:
    def __init__(
        self,
        *,
        api_key: Optional[str] = None
    ):
        try:
            import assemblyai
        except ImportError:
            raise ImportError(
                "Could not import assemblyai python package. "
                "Please install it with `pip install assemblyai`."
            )
        if api_key is not None:
            assemblyai.settings.api_key = api_key

    def to_dict(self) -> Dict[str, Any]:
        return default_to_dict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AssemblyAITranscriber":
        return default_from_dict(cls, data)
        
    @component.output_types(transcipt_object=Dict[str, Any], transcription=List[Document], summarization=List[Document], speaker_labels=List[Document])   
    def run(
        self,
        file_path: str,
        summarization: Optional[bool] = False,
        speaker_labels: Optional[bool] = False
        ):

        self.file_path = file_path

        config = aai.TranscriptionConfig(speaker_labels=speaker_labels,summarization=summarization)

        # Instantiating the Transcriber will raise a ValueError if no API key is set.
        self.transcriber = aai.Transcriber(config=config)
        transcript = self.transcriber.transcribe(self.file_path)

        ''' Not doing TypeChecking here because there is only one type of Transcript Format '''

        if transcript.error:
            raise ValueError(f"Could not transcribe file: {transcript.error}")

        transcript_json = transcript.json_response

        ''' Higher level keys cannot be used in the metadata '''
        transcript_json["transcription_id"] = transcript_json.pop("id")
        transcript_json["transcription_text"] = transcript_json.pop("text")

        # create summarization result doc
        if config.summarization:
            summarization_doc = {"summarization": [
                            Document(content=transcript.summary)
                            ]}
            transcript_json["transcription_text"] = transcript_json.pop("summary")
        else:
            summarization_doc = {}

        # create speaker labels result doc
        if config.speaker_labels:
            speakers_doc = {"speaker_labels": [
                Document(content=utterance.text, 
                         meta={"speaker": utterance.speaker}) for utterance in transcript.utterances
                         ]}
        else:
            speakers_doc = {}

            
            
            transcript_json["transcription_text"] = transcript_json.pop("utterances")

        # create transcription result doc 
        transcription_doc = {"transcription": [
            Document(content=transcript.text,
                     meta={"transcript_id":transcript.id, "audio_url":transcript.audio_url})
            ]}
        
        results = {"transcript_json": transcript_json, **transcription_doc, **summarization_doc, **speakers_doc} 
        return results