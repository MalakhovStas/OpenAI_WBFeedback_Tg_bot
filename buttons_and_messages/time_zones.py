from buttons_and_messages.base_classes import BaseButton


class BaseTimezoneButton(BaseButton):
    def _set_reply_text(self) -> str:
        return 'Время уведомлений успешно изменено'

    async def _set_answer_logic(self, update, state):
        await self.dbase.update_wb_user(
            user_id=update.from_user.id,
            update_data={'timezone_notification_times': self.name}
        )
        return self.reply_text, self.next_state


class KaliningradUtcUp2(BaseTimezoneButton):
    def _set_name(self) -> str:
        return 'Калининград (UTC +2)'


class MoscowUtcUp3(BaseTimezoneButton):
    def _set_name(self) -> str:
        return 'Москва (UTC +3)'


class SamaraUtcUp4(BaseTimezoneButton):
    def _set_name(self) -> str:
        return 'Самара (UTC +4)'


class EkaterinburgAndAktauUtcUp5(BaseTimezoneButton):
    def _set_name(self) -> str:
        return 'Екатеринбург и Актау (UTC +5)'


class OmskAndNurSultanUtcUp6(BaseTimezoneButton):
    def _set_name(self) -> str:
        return 'Омск и Нур-султан (UTC +6)'


class KrasnoyarskUtcUp7(BaseTimezoneButton):
    def _set_name(self) -> str:
        return 'Красноярск (UTC +7)'


class IrkutskUtcUp8(BaseTimezoneButton):
    def _set_name(self) -> str:
        return 'Иркутск (UTC +8)'


class YakutskUtcUp9(BaseTimezoneButton):
    def _set_name(self) -> str:
        return 'Якутск (UTC +9)'


class VladivostokUtcUp10(BaseTimezoneButton):
    def _set_name(self) -> str:
        return 'Владивосток (UTC +10)'


class MagadanUtcUp11(BaseTimezoneButton):
    def _set_name(self) -> str:
        return 'Магадан (UTC +11)'


class KamchatkaUtcUp12(BaseTimezoneButton):
    def _set_name(self) -> str:
        return 'Камчатка (UTC +12)'
