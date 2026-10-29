from fastapi import APIRouter, Depends

from .users import get_database, require_roles

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/funnel")
async def get_funnel_metrics(
    _: dict = Depends(require_roles("admin", "program_manager")),
    year: int | None = None,
) -> dict:
    db = get_database()
    query = {"year": year} if year is not None else {}
    return {
        "year": year,
        "total_candidates": await db.candidates.count_documents(query),
        "eligible_for_offer": await db.candidates.count_documents({**query, "status": "eligible_for_offer"}),
        "deployment_ready": await db.candidates.count_documents({**query, "status": "deployment_ready"}),
        "referred_to_hr": await db.candidates.count_documents({**query, "status": "referred_to_hr"}),
        "active_dropouts": await db.dropouts.count_documents(
            {"is_active": True, **({"candidate_year": year} if year is not None else {})}
        ),
    }


@router.get("/batch-performance")
async def get_batch_performance(
    _: dict = Depends(require_roles("admin", "program_manager")),
    year: int | None = None,
) -> list[dict]:
    db = get_database()
    query = {"year": year} if year is not None else {}
    batches = await db.batches.find(query).to_list(length=1000)
    results = []
    for batch in batches:
        batch_id = str(batch["_id"])
        results.append(
            {
                "batch_id": batch_id,
                "batch_name": batch["name"],
                "year": batch["year"],
                "phase": batch["phase"],
                "total_candidates": await db.candidates.count_documents({"batch_id": batch_id}),
                "deployment_ready": await db.candidates.count_documents({"batch_id": batch_id, "status": "deployment_ready"}),
            }
        )
    return results


@router.get("/year-comparison")
async def get_year_comparison(_: dict = Depends(require_roles("admin", "program_manager"))) -> list[dict]:
    db = get_database()
    years = sorted(await db.candidates.distinct("year"))
    comparison = []
    for year in years:
        comparison.append(
            {
                "year": year,
                "total_candidates": await db.candidates.count_documents({"year": year}),
                "eligible_for_offer": await db.candidates.count_documents({"year": year, "status": "eligible_for_offer"}),
                "deployment_ready": await db.candidates.count_documents({"year": year, "status": "deployment_ready"}),
                "completed_batches": await db.batches.count_documents({"year": year, "is_active": False}),
            }
        )
    return comparison
