
from celery import shared_task
from .models import Seat, SeatCSVUpload
import pandas as pd


@shared_task
def process_seat_csv_upload(upload_id):
    """
    Shared logic: works for both sync & async.
    Returns JSON-serializable dict.
    """
    try:
        upload = SeatCSVUpload.objects.get(id=upload_id)
        file_path = upload.file.path

        # Read file
        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path)

        required_cols = ['seat_no', 'name', 'email']
        if not all(col in df.columns for col in required_cols):
            raise ValueError('Missing required columns: seat_no, name, email')

        added = updated = failed = 0
        errors = []

        for idx, row in df.iterrows():
            row_num = idx + 2
            try:
                seat_no = str(row['seat_no']).strip().upper()
                if not seat_no.startswith('SEAT-'):
                    raise ValueError('Seat No must start with SEAT-')

                defaults = {
                    'name': str(row['name']).strip(),
                    'email': str(row['email']).strip(),
                    'company': str(row.get('company', '')).strip(),
                    'phone': str(row.get('phone', '')).strip(),
                    'gender': str(row.get('gender', '')).lower(),
                }

                # Validate gender
                valid_genders = {k.lower(): k for k, _ in Seat.Gender.choices}
                if defaults['gender'] and defaults['gender'] not in valid_genders:
                    defaults['gender'] = ''

                obj, created = Seat.objects.update_or_create(
                    seat_no=seat_no,
                    defaults=defaults
                )
                if created:
                    added += 1
                else:
                    updated += 1
            except Exception as e:
                failed += 1
                errors.append({'row': row_num, 'error': str(e)})

        # Update upload record
        upload.processed = True
        upload.status = 'completed'
        upload.save()

        return {
            'success': True,
            'added': added,
            'updated': updated,
            'failed': failed,
            'errors': errors
        }

    except Exception as e:
        if upload_id:
            try:
                upload = SeatCSVUpload.objects.get(id=upload_id)
                upload.status = 'failed'
                upload.save()
            except:
                pass
        return {'success': False, 'error': str(e)}