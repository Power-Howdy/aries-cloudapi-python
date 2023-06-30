from typing import Optional

from aries_cloudcontroller import (
    AcaPyClient,
    V20PresCreateRequestRequest,
    V20PresProblemReportRequest,
    V20PresRequestByFormat,
    V20PresSendRequestRequest,
    V20PresSpecByFormatRequest,
)

from app.config.log_config import get_logger
from app.exceptions.cloud_api_error import CloudApiException
from app.generic.verifier.facades.acapy_verifier import Verifier
from app.generic.verifier.models import (
    AcceptProofRequest,
    CreateProofRequest,
    RejectProofRequest,
    SendProofRequest,
)
from shared import PresentationExchange, pres_id_no_version
from shared import presentation_record_to_model as record_to_model

logger = get_logger(__name__)


class VerifierV2(Verifier):
    @classmethod
    async def get_credentials_for_request(cls, controller: AcaPyClient, proof_id: str):
        pres_ex_id = pres_id_no_version(proof_id=proof_id)
        try:
            result = await controller.present_proof_v2_0.get_matching_credentials(
                pres_ex_id=pres_ex_id
            )
        except Exception as e:
            logger.exception(
                "An unexpected error occurred while getting matching credentials."
            )
            raise CloudApiException("Failed to get credentials for request.") from e

        return result

    @classmethod
    async def get_proof_records(cls, controller: AcaPyClient):
        try:
            presentation_exchange = await controller.present_proof_v2_0.get_records()
            result = [
                record_to_model(rec) for rec in presentation_exchange.results or []
            ]
        except Exception as e:
            logger.exception("An unexpected error occurred while getting records.")
            raise CloudApiException("Failed to get proof records.") from e

        return result

    @classmethod
    async def get_proof_record(cls, controller: AcaPyClient, proof_id: str):
        pres_ex_id = pres_id_no_version(proof_id)
        try:
            presentation_exchange = await controller.present_proof_v2_0.get_record(
                pres_ex_id=pres_ex_id
            )
            result = record_to_model(presentation_exchange)
        except Exception as e:
            logger.exception("An unexpected error occurred while getting record.")
            raise CloudApiException("Failed to get proof record.") from e

        return result

    @classmethod
    async def delete_proof(cls, controller: AcaPyClient, proof_id: str):
        pres_ex_id = pres_id_no_version(proof_id=proof_id)
        try:
            await controller.present_proof_v2_0.delete_record(pres_ex_id=pres_ex_id)
        except Exception as e:
            logger.exception("An unexpected error occurred while deleting record.")
            raise CloudApiException("Failed to delete record.") from e

    @classmethod
    async def create_proof_request(
        cls,
        controller: AcaPyClient,
        proof_request: CreateProofRequest,
        comment: Optional[str] = None,
    ) -> PresentationExchange:
        try:
            proof_record = await controller.present_proof_v2_0.create_proof_request(
                body=V20PresCreateRequestRequest(
                    presentation_request=V20PresRequestByFormat(
                        indy=proof_request.proof_request
                    ),
                    comment=comment,
                    trace=False,
                )
            )
            return record_to_model(proof_record)
        except Exception as e:
            logger.exception(
                "An unexpected error occurred while creating presentation request: %r",
                e,
            )
            raise CloudApiException("Failed to create presentation request.") from e

    @classmethod
    async def send_proof_request(
        cls,
        controller: AcaPyClient,
        proof_request: SendProofRequest,
    ) -> PresentationExchange:
        try:
            presentation_exchange = (
                await controller.present_proof_v2_0.send_request_free(
                    body=V20PresSendRequestRequest(
                        connection_id=proof_request.connection_id,
                        presentation_request=V20PresRequestByFormat(
                            dif=None, indy=proof_request.proof_request
                        ),
                    )
                )
            )
            result = record_to_model(presentation_exchange)
        except Exception as e:
            logger.exception(
                "An unexpected error occurred while sending presentation request."
            )
            raise CloudApiException("Failed to send presentation request.") from e

        return result

    @classmethod
    async def accept_proof_request(
        cls, controller: AcaPyClient, proof_request: AcceptProofRequest
    ) -> PresentationExchange:
        pres_ex_id = pres_id_no_version(proof_id=proof_request.proof_id)
        try:
            presentation_record = await controller.present_proof_v2_0.send_presentation(
                pres_ex_id=pres_ex_id,
                body=V20PresSpecByFormatRequest(indy=proof_request.presentation_spec),
            )
            result = record_to_model(presentation_record)
        except Exception as e:
            logger.exception(
                "An unexpected error occurred while sending a proof presentation."
            )
            raise CloudApiException("Failed to send proof presentation.") from e

        return result

    @classmethod
    async def reject_proof_request(
        cls, controller: AcaPyClient, proof_request: RejectProofRequest
    ) -> None:
        # get the record
        pres_ex_id = pres_id_no_version(proof_id=proof_request.proof_id)
        # Report problem if desired
        if proof_request.problem_report:
            try:
                await controller.present_proof_v2_0.report_problem(
                    pres_ex_id=pres_ex_id,
                    body=V20PresProblemReportRequest(
                        description=proof_request.problem_report
                    ),
                )
            except Exception as e:
                logger.exception(
                    "An unexpected error occurred while reporting problem."
                )
                raise CloudApiException("Failed to report problem.") from e

        try:
            # delete exchange record
            await controller.present_proof_v2_0.delete_record(pres_ex_id=pres_ex_id)
        except Exception as e:
            logger.exception("An unexpected error occurred while deleting record.")
            raise CloudApiException("Failed to delete record.") from e
